# -----------------------------------------------------------------------------
# Photochomper - Duplicate Photo Finder
#
# Purpose:
#   This script implements the main functionality for Photochomper, a cross-platform
#   tool designed to help users identify and manage duplicate photos and videos
#   across large collections and directories. It supports recursive scanning,
#   configurable file type inclusion/exclusion, duplicate detection by content
#   (SHA-256 hash), metadata analysis, ranking, reporting, and scheduled scans.
# -----------------------------------------------------------------------------

import os
import sys
import hashlib
import threading
import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import argparse
from PIL import Image
try:
    import iptcinfo3  # For IPTC tags
except ImportError:
    iptcinfo3 = None
try:
    import libxmp
    from libxmp import XMPFiles, XMPMeta  # For XMP tags
except ImportError:
    libxmp = None

try:
    from rich.console import Console
    from rich.progress import Progress
except ImportError:
    print("Please install 'rich' for TUI: pip install rich")
    sys.exit(1)

from collections import defaultdict
import pandas as pd

# Initialize rich console for TUI output
console = Console()
LOG_FILE = "photochomper.log"
CONFIG_FILE = "photochomper_config.json"
BACKUP_DIR = "photochomper_backup"

# Log actions and errors to a log file
def log_action(message: str):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")

# Load configuration from JSON file
def load_config(config_path=CONFIG_FILE) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log_action(f"Error loading config: {e}")
        return {}

# Save configuration to JSON file
def save_config(config: Dict[str, Any], config_path=CONFIG_FILE):
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log_action(f"Error saving config: {e}")

# Compute SHA-256 hash of a file for duplicate detection
def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log_action(f"Error hashing file {filepath}: {e}")
        return ""

# Get basic metadata for a file (creation/modification time, size, name, path)
def get_image_metadata(filepath: str) -> Dict[str, Any]:
    meta = {}
    try:
        meta = {
            "created": os.path.getctime(filepath),
            "modified": os.path.getmtime(filepath),
            "size": os.path.getsize(filepath),
            "name": os.path.basename(filepath),
            "path": filepath,
        }
        # IPTC tags
        if iptcinfo3 is not None:
            try:
                info = iptcinfo3.IPTCInfo(filepath)
                if info:
                    meta["iptc_keywords"] = info['keywords']
                    meta["iptc_caption"] = info['caption/abstract']
            except Exception as e:
                log_action(f"Error reading IPTC for {filepath}: {e}")
        # XMP tags
        if libxmp is not None:
            try:
                xmpfile = XMPFiles(file_path=filepath)
                xmp = xmpfile.get_xmp()
                if xmp:
                    meta["xmp_keywords"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'subject')
                    meta["xmp_title"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'title')
                xmpfile.close_file()
            except Exception as e:
                log_action(f"Error reading XMP for {filepath}: {e}")
    except Exception as e:
        log_action(f"Error reading metadata for {filepath}: {e}")
    return meta

# Check if a file matches the allowed image types
def is_image_file(filename: str, types: List[str]) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in [t.lower().lstrip(".") for t in types]

# Backup a file before deletion (not currently used in main flow)
def backup_file(filepath: str):
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        dest = os.path.join(BACKUP_DIR, os.path.basename(filepath))
        if not os.path.exists(dest):
            with open(filepath, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
        log_action(f"Backed up {filepath} to {dest}")
    except Exception as e:
        log_action(f"Error backing up {filepath}: {e}")

# Find duplicate files by SHA-256 hash
def find_duplicates(dirs: List[str], types: List[str], exclude_dirs: List[str], similarity_threshold: float = 1.0) -> List[List[str]]:
    files = []
    # Recursively scan directories for image files
    for d in dirs:
        for root, _, filenames in os.walk(d):
            if any(ex in root for ex in exclude_dirs):
                continue
            for fname in filenames:
                if is_image_file(fname, types):
                    files.append(os.path.join(root, fname))
    hash_map = {}
    # Group files by their hash
    for f in files:
        h = sha256_file(f)
        if h:
            hash_map.setdefault(h, []).append(f)
    # Only return groups with more than one file (duplicates)
    return [group for group in hash_map.values() if len(group) > 1]

# Rank duplicates according to user preferences (filename/path length, modified date)
def rank_duplicates(dupe_group: List[str], path_preference: str = "shorter", filename_preference: str = None) -> List[str]:
    metas = [get_image_metadata(f) for f in dupe_group]
    metas = [m for m in metas if m]  # Remove failed metadata

    # Sort by filename length if specified, then by path length, then by modified date
    if filename_preference == "longer":
        metas.sort(key=lambda m: (-len(m.get("name", "")), -len(m.get("path", "")), -m.get("modified", 0)))
    elif filename_preference == "shorter":
        metas.sort(key=lambda m: (len(m.get("name", "")), -len(m.get("path", "")), -m.get("modified", 0)))
    elif path_preference == "longer":
        metas.sort(key=lambda m: (len(m.get("path", "")), -m.get("modified", 0)))
    else:  # shorter path
        metas.sort(key=lambda m: (-len(m.get("path", "")), -m.get("modified", 0)))
    return [m["path"] for m in metas]

# Export duplicate report to CSV and JSON formats
def export_report(dupes: List[List[str]], formats: List[str] = ["csv", "json"], out_prefix: str = None, config_path: str = None, exec_time: float = None):
    config = load_config(config_path) if config_path else load_config()
    path_preference = config.get("path_preference", "shorter")  # <-- Add this
    filename_preference = config.get("filename_preference", None)  # <-- And this
    output_base = config.get("output_base", os.path.join(os.getcwd(), "duplicates_report"))
    if out_prefix is None:
        out_prefix = output_base
    summary = []
    for group_id, group in enumerate(dupes):
        ranked = rank_duplicates(group, path_preference, filename_preference)
        master = ranked[0] if ranked else None
        if not master or len(ranked) < 2:
            continue
        master_meta = get_image_metadata(master)
        group_entry = {
            "group_id": group_id,
            "master": master,
            "master_attributes": {
                "name": master_meta.get("name"),
                "path": master_meta.get("path"),
                "size": master_meta.get("size"),
                "created": master_meta.get("created"),
                "modified": master_meta.get("modified"),
                "iptc_keywords": master_meta.get("iptc_keywords"),
                "iptc_caption": master_meta.get("iptc_caption"),
                "xmp_keywords": master_meta.get("xmp_keywords"),
                "xmp_title": master_meta.get("xmp_title"),
            },
            "duplicates": [],
        }
        master_hash = sha256_file(master)
        for dup in ranked[1:]:
            dup_hash = sha256_file(dup)
            dup_meta = get_image_metadata(dup)
            reasons = []
            if dup_hash == master_hash:
                reasons.append("hash")
            if os.path.basename(dup) == os.path.basename(master):
                reasons.append("name")
            if dup_meta.get("size") == master_meta.get("size"):
                reasons.append("size")
            if dup_meta.get("created") == master_meta.get("created"):
                reasons.append("created")
            if dup_meta.get("modified") == master_meta.get("modified"):
                reasons.append("modified")
            # IPTC/XMP tag comparison
            if dup_meta.get("iptc_keywords") and master_meta.get("iptc_keywords") and dup_meta.get("iptc_keywords") == master_meta.get("iptc_keywords"):
                reasons.append("iptc_keywords")
            if dup_meta.get("iptc_caption") and master_meta.get("iptc_caption") and dup_meta.get("iptc_caption") == master_meta.get("iptc_caption"):
                reasons.append("iptc_caption")
            if dup_meta.get("xmp_keywords") and master_meta.get("xmp_keywords") and dup_meta.get("xmp_keywords") == master_meta.get("xmp_keywords"):
                reasons.append("xmp_keywords")
            if dup_meta.get("xmp_title") and master_meta.get("xmp_title") and dup_meta.get("xmp_title") == master_meta.get("xmp_title"):
                reasons.append("xmp_title")
            score = 1.0 if dup_hash == master_hash else 0.0
            group_entry["duplicates"].append({
                "file": dup,
                "score": score,
                "reasons": "|".join(reasons),
                "name": dup_meta.get("name"),
                "path": dup_meta.get("path"),
                "size": dup_meta.get("size"),
                "created": dup_meta.get("created"),
                "modified": dup_meta.get("modified"),
                "iptc_keywords": dup_meta.get("iptc_keywords"),
                "iptc_caption": dup_meta.get("iptc_caption"),
                "xmp_keywords": dup_meta.get("xmp_keywords"),
                "xmp_title": dup_meta.get("xmp_title"),
            })
        summary.append(group_entry)

    # Write CSV output with more attributes
    if "csv" in formats:
        with open(f"{out_prefix}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "GroupID", "Master", "MasterName", "MasterPath", "MasterSize", "MasterCreated", "MasterModified",
                "MasterIPTCKeywords", "MasterIPTCCaption", "MasterXMPKeywords", "MasterXMPTitle",
                "Duplicate", "DuplicateName", "DuplicatePath", "DuplicateSize", "DuplicateCreated", "DuplicateModified",
                "DuplicateIPTCKeywords", "DuplicateIPTCCaption", "DuplicateXMPKeywords", "DuplicateXMPTitle",
                "ConfidenceScore", "Reasons"
            ])
            for entry in summary:
                for dup in entry["duplicates"]:
                    writer.writerow([
                        entry["group_id"],
                        entry["master"],
                        entry["master_attributes"]["name"],
                        entry["master_attributes"]["path"],
                        entry["master_attributes"]["size"],
                        entry["master_attributes"]["created"],
                        entry["master_attributes"]["modified"],
                        entry["master_attributes"].get("iptc_keywords"),
                        entry["master_attributes"].get("iptc_caption"),
                        entry["master_attributes"].get("xmp_keywords"),
                        entry["master_attributes"].get("xmp_title"),
                        dup["file"],
                        dup["name"],
                        dup["path"],
                        dup["size"],
                        dup["created"],
                        dup["modified"],
                        dup.get("iptc_keywords"),
                        dup.get("iptc_caption"),
                        dup.get("xmp_keywords"),
                        dup.get("xmp_title"),
                        dup["score"],
                        dup["reasons"]
                    ])
    # Write JSON output with more attributes
    if "json" in formats:
        with open(f"{out_prefix}.json", "w") as f:
            json.dump(summary, f, indent=2)
    log_action(
        f"Exported report in formats: {formats} | Config: {config_path or 'default'} | Output: {out_prefix} | Execution time: {exec_time:.2f}s"
    )

# Summarize the contents of one or more report files (CSV or JSON).
# Output is in markdown format and can be saved to a file.
def summarize_reports(report_files: List[str], output_file: str = None, summary_format: str = "markdown"):
    """
    Summarize the contents of one or more report files (CSV or JSON).
    Output includes:
      - List of input files
      - Date and time range of scans
      - List of directories scanned
      - Range of confidence scores for each directory
      - Percentage of each reason for each directory
      - List of file types with duplicates in each directory
      - Date and time the report was run
      - Output markdown file name
    """
    all_rows = []
    input_files = []
    scan_dates = []
    directories = set()
    dir_conf_scores = defaultdict(list)
    dir_reasons = defaultdict(lambda: defaultdict(int))
    dir_types = defaultdict(set)

    for report in report_files:
        input_files.append(report)
        ext = Path(report).suffix.lower()
        rows = []
        if ext == ".csv":
            with open(report, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        elif ext == ".json":
            with open(report, "r") as f:
                groups = json.load(f)
                for group in groups:
                    master_dir = Path(group["master_attributes"]["path"]).parent.as_posix()
                    for dup in group["duplicates"]:
                        row = {**group["master_attributes"], **dup, "group_id": group["group_id"], "master": group["master"]}
                        row["directory"] = master_dir
                        rows.append(row)
        all_rows.extend(rows)

    # Use pandas for easier analysis
    df = pd.DataFrame(all_rows)
    if df.empty:
        md = "# PhotoChomper Report Summary\n\nNo duplicates found.\n"
        md += f"\n**Report run:** {datetime.now().isoformat()}\n"
        if output_file:
            md += f"\n**Output file:** `{output_file}`\n"
            with open(output_file, "w") as f:
                f.write(md)
        return md

    # Date/time range
    created_times = pd.to_numeric(df.get("MasterCreated", df.get("created", pd.Series([]))), errors='coerce')
    modified_times = pd.to_numeric(df.get("MasterModified", df.get("modified", pd.Series([]))), errors='coerce')
    scan_dates = []
    if not created_times.empty and not created_times.isnull().all():
        scan_dates.append(pd.to_datetime(created_times, unit='s').min())
        scan_dates.append(pd.to_datetime(created_times, unit='s').max())
    if not modified_times.empty and not modified_times.isnull().all():
        scan_dates.append(pd.to_datetime(modified_times, unit='s').min())
        scan_dates.append(pd.to_datetime(modified_times, unit='s').max())

    # Directories
    if "MasterPath" in df.columns:
        df["directory"] = df["MasterPath"].apply(lambda p: str(Path(p).parent))
    elif "path" in df.columns:
        df["directory"] = df["path"].apply(lambda p: str(Path(p).parent))
    directories = sorted(df["directory"].unique())

    # Confidence score range per directory
    for d in directories:
        scores = pd.to_numeric(df[df["directory"] == d]["ConfidenceScore"], errors='coerce')
        if not scores.empty:
            dir_conf_scores[d] = [scores.min(), scores.max()]

    # Reasons percentage per directory
    for d in directories:
        reasons_series = df[df["directory"] == d]["Reasons"].dropna()
        total = len(reasons_series)
        reason_counts = defaultdict(int)
        for reasons in reasons_series:
            for reason in reasons.split("|"):
                reason_counts[reason] += 1
        for reason, count in reason_counts.items():
            dir_reasons[d][reason] = round(100 * count / total, 2) if total else 0

    # File types with duplicates per directory
    for d in directories:
        names = df[df["directory"] == d]["DuplicateName"].dropna().tolist()
        types = set(Path(n).suffix.lower().lstrip(".") for n in names if "." in n)
        dir_types[d] = sorted(types)

    # Markdown summary
    md = "# PhotoChomper Report Summary\n\n"
    md += f"**Report run:** {datetime.now().isoformat()}\n"
    if output_file:
        md += f"**Output file:** `{output_file}`\n"
    md += "\n"

    md += "## Input Files\n"
    for f in input_files:
        md += f"- `{f}`\n"
    md += "\n"

    md += "## Scan Date/Time Range\n"
    if scan_dates:
        md += f"- Earliest: {scan_dates[0]}\n"
        md += f"- Latest: {scan_dates[-1]}\n"
    else:
        md += "- No date/time info found\n"
    md += "\n"

    md += "## Directories Scanned\n"
    for d in directories:
        md += f"### `{d}`\n"
        # Confidence score range
        if d in dir_conf_scores:
            md += f"- Confidence Score Range: {dir_conf_scores[d][0]} to {dir_conf_scores[d][1]}\n"
        # Reasons percentages
        md += "- Reasons (%):\n"
        for reason, pct in dir_reasons[d].items():
            md += f"  - {reason}: {pct}%\n"
        # File types
        md += f"- File Types with Duplicates: {', '.join(dir_types[d]) if dir_types[d] else 'None'}\n"
        md += "\n"

    if output_file:
        with open(output_file, "w") as f:
            f.write(md)
    return

# Show help message for command-line usage
def show_help():
    console.print("[bold cyan]Photochomper Help[/bold cyan]")
    console.print("Commands:")
    console.print("  --setup      Run setup TUI")
    console.print("  --search     Run duplicate search")
    console.print("  --schedule N Schedule search every N hours")
    console.print("  --help       Show this help message")

# Interactive setup for configuration via TUI
def tui_setup():
    console.print("[bold green]Photochomper Setup[/bold green]")
    default_dirs = [str(Path.home() / "Pictures")]
    default_types = ["jpg", "jpeg", "png", "gif", "bmp", "tiff"]
    default_exclude_dirs = []
    default_similarity = 1.0
    default_path_pref = "shorter"
    default_filename_pref = None

    dirs = console.input(f"Enter directories to scan (comma separated) [{','.join(default_dirs)}]: ").strip()
    dirs = dirs.split(",") if dirs else default_dirs

    types = console.input(f"Enter file types to include (comma separated, e.g. jpg,png) [{','.join(default_types)}]: ").strip()
    types = types.split(",") if types else default_types

    exclude_dirs = console.input("Enter directories to exclude (comma separated) [none]: ").strip()
    exclude_dirs = exclude_dirs.split(",") if exclude_dirs else default_exclude_dirs

    similarity_input = console.input(f"Similarity threshold (1.0 = exact) [{default_similarity}]: ").strip()
    similarity = float(similarity_input) if similarity_input else default_similarity

    path_pref = console.input(f"Prefer master file with (shorter/longer) path? [{default_path_pref}]: ").strip().lower()
    if path_pref not in ("shorter", "longer"):
        path_pref = default_path_pref

    filename_pref = console.input("Prefer master file with (shorter/longer) filename? [none]: ").strip().lower()
    if filename_pref not in ("shorter", "longer"):
        filename_pref = default_filename_pref

    # Always create a new config file with a unique timestamp
    default_config_dir = os.getcwd()
    config_dir = console.input(f"Directory to save config file? [{default_config_dir}]: ").strip()
    if not config_dir:
        config_dir = default_config_dir

    config_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_config_base = "photochomper_config"
    config_base = console.input(f"Config file base name? [{default_config_base}]: ").strip()
    if not config_base:
        config_base = default_config_base
    # Always append date/time to config file name and use .conf extension
    config_name = f"{config_base}_{config_timestamp}.conf"
    config_path = os.path.join(config_dir, config_name)

    # Ask for output file location
    default_output_dir = os.getcwd()
    output_dir = console.input(f"Directory to save output files? [{default_output_dir}]: ").strip()
    if not output_dir:
        output_dir = default_output_dir

    default_output_base = "duplicates_report"
    output_base = console.input(f"Output file base name? [{default_output_base}]: ").strip()
    if not output_base:
        output_base = default_output_base
    include_dt = console.input("Include date and time in output file name? (y/n) [y]: ").strip().lower()
    if include_dt in ("", "y", "yes"):
        output_base += f"_{config_timestamp}"
    output_base = os.path.join(output_dir, output_base)

    config = {
        "dirs": [d.strip() for d in dirs if d.strip()],
        "types": [t.strip() for t in types if t.strip()],
        "exclude_dirs": [e.strip() for e in exclude_dirs if e.strip()],
        "similarity_threshold": similarity,
        "path_preference": path_pref,
        "filename_preference": filename_pref,
        "config_file": config_path,
        "output_base": output_base
    }
    save_config(config, config_path)
    console.print(f"[bold green]Configuration saved to {config_path}.[/bold green]")

    # Only ask for summary file name, not format
    default_summary_file = os.path.join(output_dir, "duplicates_summary.md")
    summary_file = console.input(f"Summary output file name? [{default_summary_file}]: ").strip()
    if not summary_file:
        summary_file = default_summary_file
    # Always append date/time if requested, even for custom summary file names
    if include_dt in ("", "y", "yes"):
        base, ext = os.path.splitext(summary_file)
        summary_file = f"{base}_{config_timestamp}{ext}"

    config.update({
        "summary_format": "markdown",
        "summary_file": summary_file
    })
    save_config(config, config_path)
    console.print(f"[bold green]Configuration saved to {config_path}.[/bold green]")

def select_config_file(config_dir: str) -> str:
    """Allow the user to select a config file if more than one exists in the directory."""
    configs = [f for f in os.listdir(config_dir) if f.endswith(".conf")]
    if not configs:
        console.print(f"[bold red]No config files found in {config_dir}. Running setup.[/bold red]")
        tui_setup()
        sys.exit(0)
    if len(configs) == 1:
        return os.path.join(config_dir, configs[0])
    # Warn and offer selection
    console.print(f"[bold yellow]Multiple config files found in {config_dir}:[/bold yellow]")
    for idx, fname in enumerate(configs, 1):
        console.print(f"  {idx}. {fname}")
    while True:
        choice = console.input(f"Select config file by number (1-{len(configs)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(configs):
            return os.path.join(config_dir, configs[int(choice) - 1])
        console.print("[bold red]Invalid selection. Try again.[/bold red]")

def load_config(config_path="photochomper_config.conf") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log_action(f"Error loading config: {e}")
        return {}

def save_config(config: Dict[str, Any], config_path="photochomper_config.conf"):
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log_action(f"Error saving config: {e}")

# Compute SHA-256 hash of a file for duplicate detection
def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log_action(f"Error hashing file {filepath}: {e}")
        return ""

# Get basic metadata for a file (creation/modification time, size, name, path)
def get_image_metadata(filepath: str) -> Dict[str, Any]:
    meta = {}
    try:
        meta = {
            "created": os.path.getctime(filepath),
            "modified": os.path.getmtime(filepath),
            "size": os.path.getsize(filepath),
            "name": os.path.basename(filepath),
            "path": filepath,
        }
        # IPTC tags
        if iptcinfo3 is not None:
            try:
                info = iptcinfo3.IPTCInfo(filepath)
                if info:
                    meta["iptc_keywords"] = info['keywords']
                    meta["iptc_caption"] = info['caption/abstract']
            except Exception as e:
                log_action(f"Error reading IPTC for {filepath}: {e}")
        # XMP tags
        if libxmp is not None:
            try:
                xmpfile = XMPFiles(file_path=filepath)
                xmp = xmpfile.get_xmp()
                if xmp:
                    meta["xmp_keywords"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'subject')
                    meta["xmp_title"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'title')
                xmpfile.close_file()
            except Exception as e:
                log_action(f"Error reading XMP for {filepath}: {e}")
    except Exception as e:
        log_action(f"Error reading metadata for {filepath}: {e}")
    return meta

# Check if a file matches the allowed image types
def is_image_file(filename: str, types: List[str]) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in [t.lower().lstrip(".") for t in types]

# Backup a file before deletion (not currently used in main flow)
def backup_file(filepath: str):
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        dest = os.path.join(BACKUP_DIR, os.path.basename(filepath))
        if not os.path.exists(dest):
            with open(filepath, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
        log_action(f"Backed up {filepath} to {dest}")
    except Exception as e:
        log_action(f"Error backing up {filepath}: {e}")

# Find duplicate files by SHA-256 hash
def find_duplicates(dirs: List[str], types: List[str], exclude_dirs: List[str], similarity_threshold: float = 1.0) -> List[List[str]]:
    files = []
    # Recursively scan directories for image files
    for d in dirs:
        for root, _, filenames in os.walk(d):
            if any(ex in root for ex in exclude_dirs):
                continue
            for fname in filenames:
                if is_image_file(fname, types):
                    files.append(os.path.join(root, fname))
    hash_map = {}
    # Group files by their hash
    for f in files:
        h = sha256_file(f)
        if h:
            hash_map.setdefault(h, []).append(f)
    # Only return groups with more than one file (duplicates)
    return [group for group in hash_map.values() if len(group) > 1]

# Rank duplicates according to user preferences (filename/path length, modified date)
def rank_duplicates(dupe_group: List[str], path_preference: str = "shorter", filename_preference: str = None) -> List[str]:
    metas = [get_image_metadata(f) for f in dupe_group]
    metas = [m for m in metas if m]  # Remove failed metadata

    # Sort by filename length if specified, then by path length, then by modified date
    if filename_preference == "longer":
        metas.sort(key=lambda m: (-len(m.get("name", "")), -len(m.get("path", "")), -m.get("modified", 0)))
    elif filename_preference == "shorter":
        metas.sort(key=lambda m: (len(m.get("name", "")), -len(m.get("path", "")), -m.get("modified", 0)))
    elif path_preference == "longer":
        metas.sort(key=lambda m: (len(m.get("path", "")), -m.get("modified", 0)))
    else:  # shorter path
        metas.sort(key=lambda m: (-len(m.get("path", "")), -m.get("modified", 0)))
    return [m["path"] for m in metas]

# Export duplicate report to CSV and JSON formats
def export_report(dupes: List[List[str]], formats: List[str] = ["csv", "json"], out_prefix: str = None, config_path: str = None, exec_time: float = None):
    config = load_config(config_path) if config_path else load_config()
    path_preference = config.get("path_preference", "shorter")  # <-- Add this
    filename_preference = config.get("filename_preference", None)  # <-- And this
    output_base = config.get("output_base", os.path.join(os.getcwd(), "duplicates_report"))
    if out_prefix is None:
        out_prefix = output_base
    summary = []
    for group_id, group in enumerate(dupes):
        ranked = rank_duplicates(group, path_preference, filename_preference)
        master = ranked[0] if ranked else None
        if not master or len(ranked) < 2:
            continue
        master_meta = get_image_metadata(master)
        group_entry = {
            "group_id": group_id,
            "master": master,
            "master_attributes": {
                "name": master_meta.get("name"),
                "path": master_meta.get("path"),
                "size": master_meta.get("size"),
                "created": master_meta.get("created"),
                "modified": master_meta.get("modified"),
                "iptc_keywords": master_meta.get("iptc_keywords"),
                "iptc_caption": master_meta.get("iptc_caption"),
                "xmp_keywords": master_meta.get("xmp_keywords"),
                "xmp_title": master_meta.get("xmp_title"),
            },
            "duplicates": [],
        }
        master_hash = sha256_file(master)
        for dup in ranked[1:]:
            dup_hash = sha256_file(dup)
            dup_meta = get_image_metadata(dup)
            reasons = []
            if dup_hash == master_hash:
                reasons.append("hash")
            if os.path.basename(dup) == os.path.basename(master):
                reasons.append("name")
            if dup_meta.get("size") == master_meta.get("size"):
                reasons.append("size")
            if dup_meta.get("created") == master_meta.get("created"):
                reasons.append("created")
            if dup_meta.get("modified") == master_meta.get("modified"):
                reasons.append("modified")
            # IPTC/XMP tag comparison
            if dup_meta.get("iptc_keywords") and master_meta.get("iptc_keywords") and dup_meta.get("iptc_keywords") == master_meta.get("iptc_keywords"):
                reasons.append("iptc_keywords")
            if dup_meta.get("iptc_caption") and master_meta.get("iptc_caption") and dup_meta.get("iptc_caption") == master_meta.get("iptc_caption"):
                reasons.append("iptc_caption")
            if dup_meta.get("xmp_keywords") and master_meta.get("xmp_keywords") and dup_meta.get("xmp_keywords") == master_meta.get("xmp_keywords"):
                reasons.append("xmp_keywords")
            if dup_meta.get("xmp_title") and master_meta.get("xmp_title") and dup_meta.get("xmp_title") == master_meta.get("xmp_title"):
                reasons.append("xmp_title")
            score = 1.0 if dup_hash == master_hash else 0.0
            group_entry["duplicates"].append({
                "file": dup,
                "score": score,
                "reasons": "|".join(reasons),
                "name": dup_meta.get("name"),
                "path": dup_meta.get("path"),
                "size": dup_meta.get("size"),
                "created": dup_meta.get("created"),
                "modified": dup_meta.get("modified"),
                "iptc_keywords": dup_meta.get("iptc_keywords"),
                "iptc_caption": dup_meta.get("iptc_caption"),
                "xmp_keywords": dup_meta.get("xmp_keywords"),
                "xmp_title": dup_meta.get("xmp_title"),
            })
        summary.append(group_entry)

    # Write CSV output with more attributes
    if "csv" in formats:
        with open(f"{out_prefix}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "GroupID", "Master", "MasterName", "MasterPath", "MasterSize", "MasterCreated", "MasterModified",
                "MasterIPTCKeywords", "MasterIPTCCaption", "MasterXMPKeywords", "MasterXMPTitle",
                "Duplicate", "DuplicateName", "DuplicatePath", "DuplicateSize", "DuplicateCreated", "DuplicateModified",
                "DuplicateIPTCKeywords", "DuplicateIPTCCaption", "DuplicateXMPKeywords", "DuplicateXMPTitle",
                "ConfidenceScore", "Reasons"
            ])
            for entry in summary:
                for dup in entry["duplicates"]:
                    writer.writerow([
                        entry["group_id"],
                        entry["master"],
                        entry["master_attributes"]["name"],
                        entry["master_attributes"]["path"],
                        entry["master_attributes"]["size"],
                        entry["master_attributes"]["created"],
                        entry["master_attributes"]["modified"],
                        entry["master_attributes"].get("iptc_keywords"),
                        entry["master_attributes"].get("iptc_caption"),
                        entry["master_attributes"].get("xmp_keywords"),
                        entry["master_attributes"].get("xmp_title"),
                        dup["file"],
                        dup["name"],
                        dup["path"],
                        dup["size"],
                        dup["created"],
                        dup["modified"],
                        dup.get("iptc_keywords"),
                        dup.get("iptc_caption"),
                        dup.get("xmp_keywords"),
                        dup.get("xmp_title"),
                        dup["score"],
                        dup["reasons"]
                    ])
    # Write JSON output with more attributes
    if "json" in formats:
        with open(f"{out_prefix}.json", "w") as f:
            json.dump(summary, f, indent=2)
    log_action(
        f"Exported report in formats: {formats} | Config: {config_path or 'default'} | Output: {out_prefix} | Execution time: {exec_time:.2f}s"
    )

# Summarize the contents of one or more report files (CSV or JSON).
# Output is in markdown format and can be saved to a file.
def summarize_reports(report_files: List[str], output_file: str = None, summary_format: str = "markdown"):
    """
    Summarize the contents of one or more report files (CSV or JSON).
    Output includes:
      - List of input files
      - Date and time range of scans
      - List of directories scanned
      - Range of confidence scores for each directory
      - Percentage of each reason for each directory
      - List of file types with duplicates in each directory
      - Date and time the report was run
      - Output markdown file name
    """
    all_rows = []
    input_files = []
    scan_dates = []
    directories = set()
    dir_conf_scores = defaultdict(list)
    dir_reasons = defaultdict(lambda: defaultdict(int))
    dir_types = defaultdict(set)

    for report in report_files:
        input_files.append(report)
        ext = Path(report).suffix.lower()
        rows = []
        if ext == ".csv":
            with open(report, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        elif ext == ".json":
            with open(report, "r") as f:
                groups = json.load(f)
                for group in groups:
                    master_dir = Path(group["master_attributes"]["path"]).parent.as_posix()
                    for dup in group["duplicates"]:
                        row = {**group["master_attributes"], **dup, "group_id": group["group_id"], "master": group["master"]}
                        row["directory"] = master_dir
                        rows.append(row)
        all_rows.extend(rows)

    # Use pandas for easier analysis
    df = pd.DataFrame(all_rows)
    if df.empty:
        md = "# PhotoChomper Report Summary\n\nNo duplicates found.\n"
        md += f"\n**Report run:** {datetime.now().isoformat()}\n"
        if output_file:
            md += f"\n**Output file:** `{output_file}`\n"
            with open(output_file, "w") as f:
                f.write(md)
        return md

    # Date/time range
    created_times = pd.to_numeric(df.get("MasterCreated", df.get("created", pd.Series([]))), errors='coerce')
    modified_times = pd.to_numeric(df.get("MasterModified", df.get("modified", pd.Series([]))), errors='coerce')
    scan_dates = []
    if not created_times.empty and not created_times.isnull().all():
        scan_dates.append(pd.to_datetime(created_times, unit='s').min())
        scan_dates.append(pd.to_datetime(created_times, unit='s').max())
    if not modified_times.empty and not modified_times.isnull().all():
        scan_dates.append(pd.to_datetime(modified_times, unit='s').min())
        scan_dates.append(pd.to_datetime(modified_times, unit='s').max())

    # Directories
    if "MasterPath" in df.columns:
        df["directory"] = df["MasterPath"].apply(lambda p: str(Path(p).parent))
    elif "path" in df.columns:
        df["directory"] = df["path"].apply(lambda p: str(Path(p).parent))
    directories = sorted(df["directory"].unique())

    # Confidence score range per directory
    for d in directories:
        scores = pd.to_numeric(df[df["directory"] == d]["ConfidenceScore"], errors='coerce')
        if not scores.empty:
            dir_conf_scores[d] = [scores.min(), scores.max()]

    # Reasons percentage per directory
    for d in directories:
        reasons_series = df[df["directory"] == d]["Reasons"].dropna()
        total = len(reasons_series)
        reason_counts = defaultdict(int)
        for reasons in reasons_series:
            for reason in reasons.split("|"):
                reason_counts[reason] += 1
        for reason, count in reason_counts.items():
            dir_reasons[d][reason] = round(100 * count / total, 2) if total else 0

    # File types with duplicates per directory
    for d in directories:
        names = df[df["directory"] == d]["DuplicateName"].dropna().tolist()
        types = set(Path(n).suffix.lower().lstrip(".") for n in names if "." in n)
        dir_types[d] = sorted(types)

    # Markdown summary
    md = "# PhotoChomper Report Summary\n\n"
    md += f"**Report run:** {datetime.now().isoformat()}\n"
    if output_file:
        md += f"**Output file:** `{output_file}`\n"
    md += "\n"

    md += "## Input Files\n"
    for f in input_files:
        md += f"- `{f}`\n"
    md += "\n"

    md += "## Scan Date/Time Range\n"
    if scan_dates:
        md += f"- Earliest: {scan_dates[0]}\n"
        md += f"- Latest: {scan_dates[-1]}\n"
    else:
        md += "- No date/time info found\n"
    md += "\n"

    md += "## Directories Scanned\n"
    for d in directories:
        md += f"### `{d}`\n"
        # Confidence score range
        if d in dir_conf_scores:
            md += f"- Confidence Score Range: {dir_conf_scores[d][0]} to {dir_conf_scores[d][1]}\n"
        # Reasons percentages
        md += "- Reasons (%):\n"
        for reason, pct in dir_reasons[d].items():
            md += f"  - {reason}: {pct}%\n"
        # File types
        md += f"- File Types with Duplicates: {', '.join(dir_types[d]) if dir_types[d] else 'None'}\n"
        md += "\n"

    if output_file:
        with open(output_file, "w") as f:
            f.write(md)
    return

# Show help message for command-line usage
def show_help():
    console.print("[bold cyan]Photochomper Help[/bold cyan]")
    console.print("Commands:")
    console.print("  --setup      Run setup TUI")
    console.print("  --search     Run duplicate search")
    console.print("  --schedule N Schedule search every N hours")
    console.print("  --help       Show this help message")

# Interactive setup for configuration via TUI
def tui_setup():
    console.print("[bold green]Photochomper Setup[/bold green]")
    default_dirs = [str(Path.home() / "Pictures")]
    default_types = ["jpg", "jpeg", "png", "gif", "bmp", "tiff"]
    default_exclude_dirs = []
    default_similarity = 1.0
    default_path_pref = "shorter"
    default_filename_pref = None

    dirs = console.input(f"Enter directories to scan (comma separated) [{','.join(default_dirs)}]: ").strip()
    dirs = dirs.split(",") if dirs else default_dirs

    types = console.input(f"Enter file types to include (comma separated, e.g. jpg,png) [{','.join(default_types)}]: ").strip()
    types = types.split(",") if types else default_types

    exclude_dirs = console.input("Enter directories to exclude (comma separated) [none]: ").strip()
    exclude_dirs = exclude_dirs.split(",") if exclude_dirs else default_exclude_dirs

    similarity_input = console.input(f"Similarity threshold (1.0 = exact) [{default_similarity}]: ").strip()
    similarity = float(similarity_input) if similarity_input else default_similarity

    path_pref = console.input(f"Prefer master file with (shorter/longer) path? [{default_path_pref}]: ").strip().lower()
    if path_pref not in ("shorter", "longer"):
        path_pref = default_path_pref

    filename_pref = console.input("Prefer master file with (shorter/longer) filename? [none]: ").strip().lower()
    if filename_pref not in ("shorter", "longer"):
        filename_pref = default_filename_pref

    # Always create a new config file with a unique timestamp
    default_config_dir = os.getcwd()
    config_dir = console.input(f"Directory to save config file? [{default_config_dir}]: ").strip()
    if not config_dir:
        config_dir = default_config_dir

    config_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_config_base = "photochomper_config"
    config_base = console.input(f"Config file base name? [{default_config_base}]: ").strip()
    if not config_base:
        config_base = default_config_base
    # Always append date/time to config file name and use .conf extension
    config_name = f"{config_base}_{config_timestamp}.conf"
    config_path = os.path.join(config_dir, config_name)

    # Ask for output file location
    default_output_dir = os.getcwd()
    output_dir = console.input(f"Directory to save output files? [{default_output_dir}]: ").strip()
    if not output_dir:
        output_dir = default_output_dir

    default_output_base = "duplicates_report"
    output_base = console.input(f"Output file base name? [{default_output_base}]: ").strip()
    if not output_base:
        output_base = default_output_base
    include_dt = console.input("Include date and time in output file name? (y/n) [y]: ").strip().lower()
    if include_dt in ("", "y", "yes"):
        output_base += f"_{config_timestamp}"
    output_base = os.path.join(output_dir, output_base)

    config = {
        "dirs": [d.strip() for d in dirs if d.strip()],
        "types": [t.strip() for t in types if t.strip()],
        "exclude_dirs": [e.strip() for e in exclude_dirs if e.strip()],
        "similarity_threshold": similarity,
        "path_preference": path_pref,
        "filename_preference": filename_pref,
        "config_file": config_path,
        "output_base": output_base
    }
    save_config(config, config_path)
    console.print(f"[bold green]Configuration saved to {config_path}.[/bold green]")

    # Only ask for summary file name, not format
    default_summary_file = os.path.join(output_dir, "duplicates_summary.md")
    summary_file = console.input(f"Summary output file name? [{default_summary_file}]: ").strip()
    if not summary_file:
        summary_file = default_summary_file
    # Always append date/time if requested, even for custom summary file names
    if include_dt in ("", "y", "yes"):
        base, ext = os.path.splitext(summary_file)
        summary_file = f"{base}_{config_timestamp}{ext}"

    config.update({
        "summary_format": "markdown",
        "summary_file": summary_file
    })
    save_config(config, config_path)
    console.print(f"[bold green]Configuration saved to {config_path}.[/bold green]")

def select_config_file(config_dir: str) -> str:
    """Allow the user to select a config file if more than one exists in the directory."""
    configs = [f for f in os.listdir(config_dir) if f.endswith(".conf")]
    if not configs:
        console.print(f"[bold red]No config files found in {config_dir}. Running setup.[/bold red]")
        tui_setup()
        sys.exit(0)
    if len(configs) == 1:
        return os.path.join(config_dir, configs[0])
    # Warn and offer selection
    console.print(f"[bold yellow]Multiple config files found in {config_dir}:[/bold yellow]")
    for idx, fname in enumerate(configs, 1):
        console.print(f"  {idx}. {fname}")
    while True:
        choice = console.input(f"Select config file by number (1-{len(configs)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(configs):
            return os.path.join(config_dir, configs[int(choice) - 1])
        console.print("[bold red]Invalid selection. Try again.[/bold red]")

# Run duplicate search and export results
def run_search(config: dict, config_path: str = None):
    console.print("[bold blue]Searching for duplicates...[/bold blue]")
    start_time = time.time()
    with Progress() as progress:
        task = progress.add_task("Scanning...", total=100)
        dupes = find_duplicates(
            config.get("dirs", []),
            config.get("types", []),
            config.get("exclude_dirs", []),
            config.get("similarity_threshold", 1.0)
        )
        progress.update(task, completed=100)
    exec_time = time.time() - start_time
    console.print(f"[bold yellow]{len(dupes)} duplicate groups found.[/bold yellow]")
    export_report(dupes, formats=["csv", "json"], config_path=config.get("config_file", config_path), exec_time=exec_time)
    console.print("[bold green]Reports exported to duplicates_report.csv and duplicates_report.json[/bold green]")
    log_action(
        f"Search completed: {len(dupes)} groups found | Config: {config.get('config_file', config_path) or 'default'} | Execution time: {exec_time:.2f}s"
    )
    # Print summary of total duplicate files found
    total_files = sum(len(g) for g in dupes)
    console.print(f"[bold magenta]Total duplicate files: {total_files}[/bold magenta]")

# Schedule repeated duplicate searches at a given interval (in hours)
def schedule_search(interval_hours: int, config: Dict[str, Any]):
    console.print(f"[bold blue]Scheduled search every {interval_hours} hours.[/bold blue]")
    while True:
        run_search(config)
        time.sleep(interval_hours * 3600)

# Main entry point for command-line interface
def main():
    parser = argparse.ArgumentParser(description="Photochomper - Duplicate Photo Finder")
    parser.add_argument("--setup", action="store_true", help="Run setup TUI")
    parser.add_argument("--search", action="store_true", help="Run duplicate search")
    parser.add_argument("--schedule", type=int, help="Schedule search every N hours")
    parser.add_argument("--configdir", type=str, help="Specify config directory to use")
    parser.add_argument("--config", type=str, help="Specify config file to use")
    args = parser.parse_args()

    if not (args.setup or args.search or args.schedule):
        console.print("[bold yellow]No command specified. Use --help for options.[/bold yellow]")
        parser.print_help()
        return

    # Determine config directory and file
    config_dir = args.configdir if args.configdir else os.getcwd()
    config_path = None
    if args.config:
        config_path = os.path.join(config_dir, args.config)
    else:
        config_path = select_config_file(config_dir)

    if args.setup:
        tui_setup()
        return

    config = load_config(config_path)
    if args.search:
        run_search(config, config_path)
    if args.schedule:
        schedule_search(args.schedule, config)

if __name__ == "__main__":
    main()