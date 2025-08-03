# -----------------------------------------------------------------------------
# Photochomper - Duplicate Photo Finder
#
# Purpose:
#   This script implements the main functionality for Photochomper, a cross-platform
#   tool designed to help users identify and manage duplicate photos and videos
#   across large collections and directories. It supports recursive scanning,
#   configurable file type inclusion/exclusion, duplicate detection by content
#   (SHA-256 hash), metadata analysis, ranking, reporting, and scheduled scans.
#
# Background:
#   Photochomper is intended for users with extensive photo libraries who wish to
#   organize, deduplicate, and maintain their collections efficiently. The program
#   provides a text user interface (TUI) for configuration, supports batch actions,
#   and exports reports for further processing. It is suitable for ongoing use
#   through scheduled scans and is designed to be lightweight and user-friendly.
#
# TODO:
#   - Implement advanced image similarity algorithms (beyond SHA-256 hash)
#   - Support EXIF, GPS, camera model, lens, and other metadata extraction
#   - Add support for video formats (MP4, AVI, MOV, etc.)
#   - Analyze image quality (resolution, sharpness, color balance, etc.)
#   - Enable tagging, rating, and custom actions for duplicates
#   - Provide backup mechanism before deletion
#   - Support batch processing and custom rules for duplicate handling
#   - Export and import reports in CSV and JSON formats
#   - Generate summary and custom reports based on user criteria
#   - Implement notifications and alerts for duplicate events
#   - Add localization/multi-language support
#   - Enhance ranking logic with all specified characteristics
#   - Add scheduling via OS task scheduler or background service
#   - Comprehensive user documentation and troubleshooting guide
#   - Implement unit tests for reliability
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

try:
    from rich.console import Console
    from rich.progress import Progress
except ImportError:
    print("Please install 'rich' for TUI: pip install rich")
    sys.exit(1)

console = Console()
LOG_FILE = "photochomper.log"
CONFIG_FILE = "photochomper_config.json"
BACKUP_DIR = "photochomper_backup"

def log_action(message: str):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")

def load_config(config_path=CONFIG_FILE) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log_action(f"Error loading config: {e}")
        return {}

def save_config(config: Dict[str, Any], config_path=CONFIG_FILE):
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log_action(f"Error saving config: {e}")

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

def get_image_metadata(filepath: str) -> Dict[str, Any]:
    try:
        return {
            "created": os.path.getctime(filepath),
            "modified": os.path.getmtime(filepath),
            "size": os.path.getsize(filepath),
            "name": os.path.basename(filepath),
            "path": filepath,
            # Add EXIF, GPS, camera model, etc.
        }
    except Exception as e:
        log_action(f"Error reading metadata for {filepath}: {e}")
        return {}

def is_image_file(filename: str, types: List[str]) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in [t.lower().lstrip(".") for t in types]

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

def find_duplicates(dirs: List[str], types: List[str], exclude_dirs: List[str], similarity_threshold: float = 1.0) -> List[List[str]]:
    files = []
    for d in dirs:
        for root, _, filenames in os.walk(d):
            if any(ex in root for ex in exclude_dirs):
                continue
            for fname in filenames:
                if is_image_file(fname, types):
                    files.append(os.path.join(root, fname))
    hash_map = {}
    for f in files:
        h = sha256_file(f)
        if h:
            hash_map.setdefault(h, []).append(f)
    return [group for group in hash_map.values() if len(group) > 1]

def rank_duplicates(dupe_group: List[str]) -> List[str]:
    metas = [get_image_metadata(f) for f in dupe_group]
    metas = [m for m in metas if m]  # Remove failed metadata
    metas.sort(key=lambda m: (-m.get("modified", 0), len(m.get("name", ""))))
    return [m["path"] for m in metas]

def export_report(dupes: List[List[str]], formats: List[str] = ["csv", "json"], out_prefix: str = "duplicates_report"):
    summary = []
    for i, group in enumerate(dupes):
        ranked = rank_duplicates(group)
        summary.append({
            "group": i,
            "master": ranked[0] if ranked else "",
            "duplicates": ranked[1:] if len(ranked) > 1 else [],
            "count": len(group)
        })
    if "csv" in formats:
        with open(f"{out_prefix}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Group", "Master", "Duplicate", "Count"])
            for s in summary:
                for dup in s["duplicates"]:
                    writer.writerow([s["group"], s["master"], dup, s["count"]])
    if "json" in formats:
        with open(f"{out_prefix}.json", "w") as f:
            json.dump(summary, f, indent=2)
    log_action(f"Exported report in formats: {formats}")

def show_help():
    console.print("[bold cyan]Photochomper Help[/bold cyan]")
    console.print("Commands:")
    console.print("  --setup      Run setup TUI")
    console.print("  --search     Run duplicate search")
    console.print("  --schedule N Schedule search every N hours")
    console.print("  --help       Show this help message")

def tui_setup():
    console.print("[bold green]Photochomper Setup[/bold green]")
    dirs = console.input("Enter directories to scan (comma separated): ").split(",")
    types = console.input("Enter file types to include (comma separated, e.g. jpg,png): ").split(",")
    exclude_dirs = console.input("Enter directories to exclude (comma separated): ").split(",")
    similarity = float(console.input("Similarity threshold (1.0 = exact): "))
    config = {
        "dirs": [d.strip() for d in dirs if d.strip()],
        "types": [t.strip() for t in types if t.strip()],
        "exclude_dirs": [e.strip() for e in exclude_dirs if e.strip()],
        "similarity_threshold": similarity
    }
    save_config(config)
    console.print("[bold green]Configuration saved.[/bold green]")

def run_search(config: Dict[str, Any]):
    console.print("[bold blue]Searching for duplicates...[/bold blue]")
    with Progress() as progress:
        task = progress.add_task("Scanning...", total=100)
        dupes = find_duplicates(
            config.get("dirs", []),
            config.get("types", []),
            config.get("exclude_dirs", []),
            config.get("similarity_threshold", 1.0)
        )
        progress.update(task, completed=100)
    console.print(f"[bold yellow]{len(dupes)} duplicate groups found.[/bold yellow]")
    export_report(dupes, formats=["csv", "json"])
    console.print("[bold green]Reports exported to duplicates_report.csv and duplicates_report.json[/bold green]")
    log_action(f"Search completed: {len(dupes)} groups found")
    # Summary
    total_files = sum(len(g) for g in dupes)
    console.print(f"[bold magenta]Total duplicate files: {total_files}[/bold magenta]")

def schedule_search(interval_hours: int, config: Dict[str, Any]):
    console.print(f"[bold blue]Scheduled search every {interval_hours} hours.[/bold blue]")
    while True:
        run_search(config)
        time.sleep(interval_hours * 3600)

def main():
    parser = argparse.ArgumentParser(description="Photochomper - Duplicate Photo Finder")
    parser.add_argument("--setup", action="store_true", help="Run setup TUI")
    parser.add_argument("--search", action="store_true", help="Run duplicate search")
    parser.add_argument("--schedule", type=int, help="Schedule search every N hours")
    parser.add_argument("--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.help:
        show_help()
        return
    if args.setup:
        tui_setup()
    config = load_config()
    if args.search:
        run_search(config)
    if args.schedule:
        schedule_search(args.schedule, config)

if __name__ == "__main__":
    main()