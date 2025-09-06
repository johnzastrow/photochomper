import csv
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import pandas as pd
from src.config import load_config, log_action
from src.scanner import get_image_metadata, sha256_file, rank_duplicates, HashAlgorithm


def export_report(
    dupes: List[List[str]],
    formats: List[str] = ["csv", "json"],
    out_prefix: str = None,
    config_path: str = None,
    exec_time: float = None,
    progress_callback=None,
):
    config = load_config(config_path) if config_path else load_config()
    path_preference = config.get("path_preference", "shorter")
    filename_preference = config.get("filename_preference", None)
    quality_ranking = config.get("quality_ranking", False)
    hash_algorithm = config.get("hash_algorithm", "dhash")
    output_base = config.get(
        "output_base", os.path.join(os.getcwd(), "duplicates_report")
    )
    if out_prefix is None:
        out_prefix = output_base
    summary = []
    files_processed = 0
    total_files = sum(len(group) for group in dupes)

    try:
        for group_id, group in enumerate(dupes):
            try:
                log_action(f"Processing duplicate group {group_id + 1}/{len(dupes)} with {len(group)} files")
                
                ranked = rank_duplicates(
                    group, path_preference, filename_preference, quality_ranking
                )
                master = ranked[0] if ranked else None
                if not master or len(ranked) < 2:
                    log_action(f"Skipping group {group_id + 1}: insufficient files or no master")
                    continue
                    
                log_action(f"Getting metadata for master file: {master}")
                master_meta = get_image_metadata(master)
                files_processed += 1
                if progress_callback:
                    progress_callback(files_processed)
                log_action(f"Master metadata extracted, progress: {files_processed}/{total_files}")
                
            except Exception as e:
                log_action(f"Error processing group {group_id + 1}: {e}")
                continue  # Skip this group and continue with next

            group_entry = {
                "group_id": group_id,
                "master": master,
                "master_attributes": {
                    "name": master_meta.get("name"),
                    "path": master_meta.get("path"),
                    "size": master_meta.get("size"),
                    "created": master_meta.get("created"),
                    "modified": master_meta.get("modified"),
                    "width": master_meta.get("width"),
                    "height": master_meta.get("height"),
                    "file_type": master_meta.get("file_type"),
                    "camera_make": master_meta.get("camera_make"),
                    "camera_model": master_meta.get("camera_model"),
                    "date_taken": master_meta.get("date_taken"),
                    "quality_score": master_meta.get("quality_score"),
                    "iptc_keywords": master_meta.get("iptc_keywords"),
                    "iptc_caption": master_meta.get("iptc_caption"),
                    "xmp_keywords": master_meta.get("xmp_keywords"),
                    "xmp_title": master_meta.get("xmp_title"),
                },
                "duplicates": [],
            }
            # Calculate similarity using the configured algorithm
            try:
                algorithm = HashAlgorithm(hash_algorithm)
            except ValueError:
                algorithm = HashAlgorithm.DHASH

            master_hash = sha256_file(master) if algorithm == HashAlgorithm.SHA256 else ""

            for dup_idx, dup in enumerate(ranked[1:], 1):
                try:
                    log_action(f"Processing duplicate {dup_idx}/{len(ranked)-1} in group {group_id + 1}: {dup}")
                    dup_meta = get_image_metadata(dup)
                    files_processed += 1
                    if progress_callback:
                        progress_callback(files_processed)
                    log_action(f"Duplicate metadata extracted, progress: {files_processed}/{total_files}")
                    reasons = []

                    # Hash-based comparison
                    if algorithm == HashAlgorithm.SHA256:
                        dup_hash = sha256_file(dup)
                        score = 0.0 if dup_hash == master_hash else 1.0
                        if dup_hash == master_hash:
                            reasons.append("exact_hash")
                    else:
                        # For perceptual hashes, we'd need to recalculate or store them
                        # For now, assume they're similar since they're in the same group
                        score = 0.1  # Default similarity for grouped items
                        reasons.append("perceptual_hash")

                    # File attribute comparisons
                    if os.path.basename(dup) == os.path.basename(master):
                        reasons.append("same_filename")
                    if dup_meta.get("size") == master_meta.get("size"):
                        reasons.append("same_size")
                    if dup_meta.get("created") == master_meta.get("created"):
                        reasons.append("same_created_date")
                    if dup_meta.get("modified") == master_meta.get("modified"):
                        reasons.append("same_modified_date")

                    # Dimension comparison
                    if dup_meta.get("width") == master_meta.get("width") and dup_meta.get(
                        "height"
                    ) == master_meta.get("height"):
                        reasons.append("same_dimensions")

                    # Camera/EXIF comparison
                    if (
                        dup_meta.get("camera_make")
                        and master_meta.get("camera_make")
                        and dup_meta.get("camera_make") == master_meta.get("camera_make")
                    ):
                        reasons.append("same_camera_make")
                    if (
                        dup_meta.get("camera_model")
                        and master_meta.get("camera_model")
                        and dup_meta.get("camera_model") == master_meta.get("camera_model")
                    ):
                        reasons.append("same_camera_model")
                    if (
                        dup_meta.get("date_taken")
                        and master_meta.get("date_taken")
                        and dup_meta.get("date_taken") == master_meta.get("date_taken")
                    ):
                        reasons.append("same_date_taken")

                    # IPTC/XMP tag comparison
                    if (
                        dup_meta.get("iptc_keywords")
                        and master_meta.get("iptc_keywords")
                        and dup_meta.get("iptc_keywords") == master_meta.get("iptc_keywords")
                    ):
                        reasons.append("same_iptc_keywords")
                    if (
                        dup_meta.get("iptc_caption")
                        and master_meta.get("iptc_caption")
                        and dup_meta.get("iptc_caption") == master_meta.get("iptc_caption")
                    ):
                        reasons.append("same_iptc_caption")
                    if (
                        dup_meta.get("xmp_keywords")
                        and master_meta.get("xmp_keywords")
                        and dup_meta.get("xmp_keywords") == master_meta.get("xmp_keywords")
                    ):
                        reasons.append("same_xmp_keywords")
                    if (
                        dup_meta.get("xmp_title")
                        and master_meta.get("xmp_title")
                        and dup_meta.get("xmp_title") == master_meta.get("xmp_title")
                    ):
                        reasons.append("same_xmp_title")
                    group_entry["duplicates"].append(
                        {
                            "file": dup,
                            "score": score,
                            "reasons": "|".join(reasons),
                            "name": dup_meta.get("name"),
                            "path": dup_meta.get("path"),
                            "size": dup_meta.get("size"),
                            "created": dup_meta.get("created"),
                            "modified": dup_meta.get("modified"),
                            "width": dup_meta.get("width"),
                            "height": dup_meta.get("height"),
                            "file_type": dup_meta.get("file_type"),
                            "camera_make": dup_meta.get("camera_make"),
                            "camera_model": dup_meta.get("camera_model"),
                            "date_taken": dup_meta.get("date_taken"),
                            "quality_score": dup_meta.get("quality_score"),
                            "iptc_keywords": dup_meta.get("iptc_keywords"),
                            "iptc_caption": dup_meta.get("iptc_caption"),
                            "xmp_keywords": dup_meta.get("xmp_keywords"),
                            "xmp_title": dup_meta.get("xmp_title"),
                        }
                    )
                except Exception as e:
                    log_action(f"Error processing duplicate {dup}: {e}")
                    continue  # Skip this duplicate and continue with next
            summary.append(group_entry)

    except KeyboardInterrupt:
        log_action(
            f"Report generation interrupted by user. Processed {files_processed}/{total_files} files."
        )
        print(
            f"\n⚠️  Report generation interrupted. Processed {files_processed}/{total_files} files."
        )
        print("Partial report data will be saved with completed entries.")

    # Write CSV output with more attributes
    if "csv" in formats:
        with open(f"{out_prefix}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "GroupID",
                    "Algorithm",
                    "Master",
                    "File",
                    "Name",
                    "Path",
                    "Size",
                    "Created",
                    "Modified",
                    "Width",
                    "Height",
                    "FileType",
                    "CameraMake",
                    "CameraModel",
                    "DateTaken",
                    "QualityScore",
                    "IPTCKeywords",
                    "IPTCCaption",
                    "XMPKeywords",
                    "XMPTitle",
                    "SimilarityScore",
                    "MatchReasons",
                ]
            )
            for entry in summary:
                # Write master file first
                writer.writerow(
                    [
                        entry["group_id"],
                        hash_algorithm,
                        "Yes",  # Master column
                        entry["master"],
                        entry["master_attributes"]["name"],
                        entry["master_attributes"]["path"],
                        entry["master_attributes"]["size"],
                        entry["master_attributes"]["created"],
                        entry["master_attributes"]["modified"],
                        entry["master_attributes"].get("width"),
                        entry["master_attributes"].get("height"),
                        entry["master_attributes"].get("file_type"),
                        entry["master_attributes"].get("camera_make"),
                        entry["master_attributes"].get("camera_model"),
                        entry["master_attributes"].get("date_taken"),
                        entry["master_attributes"].get("quality_score"),
                        entry["master_attributes"].get("iptc_keywords"),
                        entry["master_attributes"].get("iptc_caption"),
                        entry["master_attributes"].get("xmp_keywords"),
                        entry["master_attributes"].get("xmp_title"),
                        "",  # No similarity score for master
                        "",  # No match reasons for master
                    ]
                )
                # Write duplicate files
                for dup in entry["duplicates"]:
                    writer.writerow(
                        [
                            entry["group_id"],
                            hash_algorithm,
                            "",  # Master column - empty for duplicates
                            dup["file"],
                            dup["name"],
                            dup["path"],
                            dup["size"],
                            dup["created"],
                            dup["modified"],
                            dup.get("width"),
                            dup.get("height"),
                            dup.get("file_type"),
                            dup.get("camera_make"),
                            dup.get("camera_model"),
                            dup.get("date_taken"),
                            dup.get("quality_score"),
                            dup.get("iptc_keywords"),
                            dup.get("iptc_caption"),
                            dup.get("xmp_keywords"),
                            dup.get("xmp_title"),
                            dup["score"],
                            dup["reasons"],
                        ]
                    )
    # Write JSON output with more attributes
    if "json" in formats:
        with open(f"{out_prefix}.json", "w") as f:
            json.dump(summary, f, indent=2)

    # Write SQLite database output
    if "sqlite" in formats:
        create_sqlite_database(summary, f"{out_prefix}.db", hash_algorithm, exec_time)

    log_action(
        f"Exported report in formats: {formats} | Config: {config_path or 'default'} | Output: {out_prefix} | Execution time: {exec_time:.2f}s"
    )


def create_sqlite_database(
    summary: List[Dict], db_path: str, hash_algorithm: str, exec_time: float = None
):
    """
    Create SQLite database with duplicate file data and useful analysis views.

    Args:
        summary: List of duplicate group dictionaries
        db_path: Path to SQLite database file
        hash_algorithm: Hash algorithm used
        exec_time: Execution time for metadata
    """
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create main duplicates table with primary key
    cursor.execute("""
        CREATE TABLE duplicates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            algorithm TEXT NOT NULL,
            master TEXT NOT NULL,
            file TEXT NOT NULL,
            name TEXT,
            path TEXT,
            size INTEGER,
            created TEXT,
            modified TEXT,
            width INTEGER,
            height INTEGER,
            file_type TEXT,
            camera_make TEXT,
            camera_model TEXT,
            date_taken TEXT,
            quality_score INTEGER,
            iptc_keywords TEXT,
            iptc_caption TEXT,
            xmp_keywords TEXT,
            xmp_title TEXT,
            similarity_score REAL,
            match_reasons TEXT
        )
    """)

    # Create indexes for better query performance
    cursor.execute("CREATE INDEX idx_group_id ON duplicates(group_id)")
    cursor.execute("CREATE INDEX idx_master ON duplicates(master)")
    cursor.execute("CREATE INDEX idx_file ON duplicates(file)")
    cursor.execute("CREATE INDEX idx_size ON duplicates(size)")
    cursor.execute("CREATE INDEX idx_camera_make ON duplicates(camera_make)")
    cursor.execute("CREATE INDEX idx_file_type ON duplicates(file_type)")

    # Insert data
    for entry in summary:
        # Insert master file first
        cursor.execute(
            """
            INSERT INTO duplicates (
                group_id, algorithm, master, file, name, path, size, created, modified,
                width, height, file_type, camera_make, camera_model, date_taken,
                quality_score, iptc_keywords, iptc_caption, xmp_keywords, xmp_title,
                similarity_score, match_reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entry["group_id"],
                hash_algorithm,
                "Yes",  # Master column
                entry["master"],
                entry["master_attributes"]["name"],
                entry["master_attributes"]["path"],
                entry["master_attributes"]["size"],
                entry["master_attributes"]["created"],
                entry["master_attributes"]["modified"],
                entry["master_attributes"].get("width"),
                entry["master_attributes"].get("height"),
                entry["master_attributes"].get("file_type"),
                entry["master_attributes"].get("camera_make"),
                entry["master_attributes"].get("camera_model"),
                entry["master_attributes"].get("date_taken"),
                entry["master_attributes"].get("quality_score"),
                entry["master_attributes"].get("iptc_keywords"),
                entry["master_attributes"].get("iptc_caption"),
                entry["master_attributes"].get("xmp_keywords"),
                entry["master_attributes"].get("xmp_title"),
                None,  # No similarity score for master
                None,  # No match reasons for master
            ),
        )

        # Insert duplicate files
        for dup in entry["duplicates"]:
            cursor.execute(
                """
                INSERT INTO duplicates (
                    group_id, algorithm, master, file, name, path, size, created, modified,
                    width, height, file_type, camera_make, camera_model, date_taken,
                    quality_score, iptc_keywords, iptc_caption, xmp_keywords, xmp_title,
                    similarity_score, match_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry["group_id"],
                    hash_algorithm,
                    "",  # Master column - empty for duplicates
                    dup["file"],
                    dup["name"],
                    dup["path"],
                    dup["size"],
                    dup["created"],
                    dup["modified"],
                    dup.get("width"),
                    dup.get("height"),
                    dup.get("file_type"),
                    dup.get("camera_make"),
                    dup.get("camera_model"),
                    dup.get("date_taken"),
                    dup.get("quality_score"),
                    dup.get("iptc_keywords"),
                    dup.get("iptc_caption"),
                    dup.get("xmp_keywords"),
                    dup.get("xmp_title"),
                    dup["score"],
                    dup["reasons"],
                ),
            )

    # Create useful analysis views
    create_analysis_views(cursor)

    # Add metadata table
    cursor.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute(
        "INSERT INTO metadata VALUES (?, ?)", ("created_at", datetime.now().isoformat())
    )
    cursor.execute("INSERT INTO metadata VALUES (?, ?)", ("algorithm", hash_algorithm))
    if exec_time:
        cursor.execute(
            "INSERT INTO metadata VALUES (?, ?)",
            ("execution_time_seconds", str(exec_time)),
        )
    cursor.execute(
        "INSERT INTO metadata VALUES (?, ?)", ("total_groups", str(len(summary)))
    )
    cursor.execute(
        "INSERT INTO metadata VALUES (?, ?)",
        ("total_files", str(sum(len(g["duplicates"]) + 1 for g in summary))),
    )

    conn.commit()
    conn.close()

    log_action(f"Created SQLite database: {db_path}")


def create_analysis_views(cursor):
    """Create useful views for analyzing duplicate data."""

    # View: Summary statistics
    cursor.execute("""
        CREATE VIEW summary_stats AS
        SELECT 
            COUNT(DISTINCT group_id) as total_groups,
            COUNT(*) as total_files,
            COUNT(CASE WHEN master = 'Yes' THEN 1 END) as master_files,
            COUNT(CASE WHEN master = '' THEN 1 END) as duplicate_files,
            ROUND(AVG(size), 0) as avg_file_size,
            SUM(size) as total_size,
            COUNT(DISTINCT file_type) as file_types_count,
            COUNT(DISTINCT camera_make) as camera_makes_count
        FROM duplicates
    """)

    # View: Groups by size (largest first)
    cursor.execute("""
        CREATE VIEW groups_by_size AS
        SELECT 
            group_id,
            COUNT(*) as files_in_group,
            SUM(size) as total_group_size,
            AVG(size) as avg_file_size,
            MIN(created) as earliest_created,
            MAX(created) as latest_created,
            GROUP_CONCAT(DISTINCT file_type) as file_types,
            GROUP_CONCAT(DISTINCT camera_make) as camera_makes
        FROM duplicates
        GROUP BY group_id
        ORDER BY files_in_group DESC, total_group_size DESC
    """)

    # View: Masters with their duplicate counts
    cursor.execute("""
        CREATE VIEW masters_summary AS
        SELECT 
            d1.group_id,
            d1.file as master_file,
            d1.name as master_name,
            d1.size as master_size,
            d1.camera_make,
            d1.camera_model,
            d1.created,
            COUNT(d2.id) as duplicate_count,
            SUM(d2.size) as duplicates_total_size,
            ROUND(SUM(d2.size) * 100.0 / (d1.size + SUM(d2.size)), 2) as space_savings_percent
        FROM duplicates d1
        LEFT JOIN duplicates d2 ON d1.group_id = d2.group_id AND d2.master = ''
        WHERE d1.master = 'Yes'
        GROUP BY d1.group_id, d1.file
        ORDER BY duplicate_count DESC, duplicates_total_size DESC
    """)

    # View: File type analysis
    cursor.execute("""
        CREATE VIEW file_type_analysis AS
        SELECT 
            file_type,
            COUNT(*) as file_count,
            COUNT(CASE WHEN master = 'Yes' THEN 1 END) as master_count,
            COUNT(CASE WHEN master = '' THEN 1 END) as duplicate_count,
            ROUND(AVG(size), 0) as avg_size,
            SUM(size) as total_size,
            COUNT(DISTINCT group_id) as groups_involved
        FROM duplicates
        WHERE file_type IS NOT NULL
        GROUP BY file_type
        ORDER BY file_count DESC
    """)

    # View: Camera analysis
    cursor.execute("""
        CREATE VIEW camera_analysis AS
        SELECT 
            camera_make,
            camera_model,
            COUNT(*) as file_count,
            COUNT(CASE WHEN master = 'Yes' THEN 1 END) as master_count,
            COUNT(CASE WHEN master = '' THEN 1 END) as duplicate_count,
            COUNT(DISTINCT group_id) as groups_involved,
            ROUND(AVG(size), 0) as avg_size,
            SUM(size) as total_size
        FROM duplicates
        WHERE camera_make IS NOT NULL AND camera_model IS NOT NULL
        GROUP BY camera_make, camera_model
        ORDER BY file_count DESC
    """)

    # View: Size analysis (potential space savings)
    cursor.execute("""
        CREATE VIEW size_analysis AS
        SELECT 
            CASE 
                WHEN size < 1024*1024 THEN 'Under 1MB'
                WHEN size < 5*1024*1024 THEN '1-5MB'
                WHEN size < 10*1024*1024 THEN '5-10MB' 
                WHEN size < 50*1024*1024 THEN '10-50MB'
                ELSE 'Over 50MB'
            END as size_category,
            COUNT(*) as file_count,
            COUNT(CASE WHEN master = 'Yes' THEN 1 END) as master_count,
            COUNT(CASE WHEN master = '' THEN 1 END) as duplicate_count,
            ROUND(AVG(size), 0) as avg_size,
            SUM(size) as total_size,
            SUM(CASE WHEN master = '' THEN size ELSE 0 END) as potential_savings
        FROM duplicates
        GROUP BY size_category
        ORDER BY 
            CASE size_category
                WHEN 'Under 1MB' THEN 1
                WHEN '1-5MB' THEN 2
                WHEN '5-10MB' THEN 3
                WHEN '10-50MB' THEN 4
                ELSE 5
            END
    """)

    # View: Duplicate reasons analysis
    cursor.execute("""
        CREATE VIEW match_reasons_analysis AS
        SELECT 
            match_reasons,
            COUNT(*) as occurrence_count,
            ROUND(AVG(similarity_score), 3) as avg_similarity_score,
            ROUND(AVG(size), 0) as avg_file_size
        FROM duplicates
        WHERE match_reasons IS NOT NULL AND match_reasons != ''
        GROUP BY match_reasons
        ORDER BY occurrence_count DESC
    """)

    # View: Directory analysis
    cursor.execute("""
        CREATE VIEW directory_analysis AS
        SELECT 
            path,
            COUNT(*) as file_count,
            COUNT(CASE WHEN master = 'Yes' THEN 1 END) as master_count,
            COUNT(CASE WHEN master = '' THEN 1 END) as duplicate_count,
            COUNT(DISTINCT group_id) as groups_involved,
            SUM(size) as total_size,
            SUM(CASE WHEN master = '' THEN size ELSE 0 END) as potential_savings
        FROM duplicates
        WHERE path IS NOT NULL
        GROUP BY path
        ORDER BY file_count DESC
    """)


def summarize_reports(
    report_files: List[str], output_file: str = None, summary_format: str = "markdown"
):
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
                    master_dir = Path(
                        group["master_attributes"]["path"]
                    ).parent.as_posix()
                    for dup in group["duplicates"]:
                        row = {
                            **group["master_attributes"],
                            **dup,
                            "group_id": group["group_id"],
                            "master": group["master"],
                        }
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
    created_times = pd.to_numeric(
        df.get("MasterCreated", df.get("created", pd.Series([]))), errors="coerce"
    )
    modified_times = pd.to_numeric(
        df.get("MasterModified", df.get("modified", pd.Series([]))), errors="coerce"
    )
    scan_dates = []
    if not created_times.empty and not created_times.isnull().all():
        scan_dates.append(pd.to_datetime(created_times, unit="s").min())
        scan_dates.append(pd.to_datetime(created_times, unit="s").max())
    if not modified_times.empty and not modified_times.isnull().all():
        scan_dates.append(pd.to_datetime(modified_times, unit="s").min())
        scan_dates.append(pd.to_datetime(modified_times, unit="s").max())

    # Directories - handle NaN values safely
    def safe_path_parent(p):
        if pd.isna(p) or p is None:
            return "unknown"
        try:
            return str(Path(str(p)).parent)
        except:
            return "unknown"

    if "MasterPath" in df.columns:
        df["directory"] = df["MasterPath"].apply(safe_path_parent)
    elif "path" in df.columns:
        df["directory"] = df["path"].apply(safe_path_parent)
    else:
        df["directory"] = "unknown"

    directories = sorted(df["directory"].unique())

    # Count files per directory
    dir_file_counts = {}
    dir_duplicate_counts = {}
    for d in directories:
        dir_files = df[df["directory"] == d]
        # Count unique master files
        if "Master" in dir_files.columns:
            unique_masters = dir_files["Master"].nunique()
        elif "master" in dir_files.columns:
            unique_masters = dir_files["master"].nunique()
        else:
            unique_masters = 0

        # Count total duplicates
        total_duplicates = len(dir_files)

        dir_file_counts[d] = unique_masters
        dir_duplicate_counts[d] = total_duplicates

    # Confidence score range per directory
    for d in directories:
        if "ConfidenceScore" in df.columns:
            scores = pd.to_numeric(
                df[df["directory"] == d]["ConfidenceScore"], errors="coerce"
            ).dropna()
            if not scores.empty:
                dir_conf_scores[d] = [scores.min(), scores.max()]

    # Reasons percentage per directory
    for d in directories:
        if "Reasons" in df.columns:
            reasons_series = df[df["directory"] == d]["Reasons"].dropna()
            total = len(reasons_series)
            reason_counts = defaultdict(int)
            for reasons in reasons_series:
                if isinstance(reasons, str):
                    for reason in reasons.split("|"):
                        if reason.strip():  # Skip empty reasons
                            reason_counts[reason.strip()] += 1
            for reason, count in reason_counts.items():
                dir_reasons[d][reason] = round(100 * count / total, 2) if total else 0

    # File types with duplicates per directory
    for d in directories:
        if "DuplicateName" in df.columns:
            names = df[df["directory"] == d]["DuplicateName"].dropna().tolist()
            types = set()
            for n in names:
                if isinstance(n, str) and "." in n:
                    ext = Path(n).suffix.lower().lstrip(".")
                    if ext:  # Skip empty extensions
                        types.add(ext)
            dir_types[d] = sorted(types)

    # Detect search parameters from data
    search_params = {}
    if not df.empty:
        # Try to infer algorithm from confidence scores and reasons
        if "ConfidenceScore" in df.columns:
            scores = pd.to_numeric(df["ConfidenceScore"], errors="coerce").dropna()
            if not scores.empty:
                if scores.min() == scores.max() == 1.0:
                    search_params["algorithm"] = "SHA-256 (exact matching)"
                elif scores.min() < 1.0:
                    search_params["algorithm"] = (
                        "Perceptual hashing (similarity matching)"
                    )

        # Detect file types from extensions
        all_files = []
        if "Master" in df.columns:
            all_files.extend(df["Master"].dropna().tolist())
        if "DuplicateName" in df.columns:
            all_files.extend(df["DuplicateName"].dropna().tolist())
        elif "file" in df.columns:
            all_files.extend(df["file"].dropna().tolist())

        if all_files:
            extensions = set()
            for f in all_files:
                if isinstance(f, str) and "." in f:
                    ext = Path(f).suffix.lower().lstrip(".")
                    if ext:
                        extensions.add(ext)
            search_params["file_types"] = sorted(extensions)

    # Markdown summary with enhanced explanations
    md = "# PhotoChomper Duplicate Detection Report Summary\n\n"
    md += f"**Report generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    if output_file:
        md += f"**Output file:** `{output_file}`\n"
    md += "\n"

    # Executive Summary
    md += "## Executive Summary\n\n"
    total_groups = (
        df["group_id"].nunique()
        if "group_id" in df.columns
        else df["GroupID"].nunique()
        if "GroupID" in df.columns
        else 0
    )
    total_duplicates = len(df)
    total_directories = len(directories)

    md += f"This report summarizes duplicate file detection results from {len(input_files)} report file(s). "
    md += f"**{total_groups} duplicate groups** were found containing **{total_duplicates} duplicate files** "
    md += f"across **{total_directories} directories**.\n\n"

    # Input Files section
    md += "## Input Report Files\n\n"
    md += "*This section lists the report files that were processed to generate this summary.*\n\n"
    for f in input_files:
        md += f"- `{f}`\n"
    md += "\n"

    # Search Parameters section
    if search_params:
        md += "## Detection Parameters\n\n"
        md += (
            "*These parameters were inferred from the duplicate detection results.*\n\n"
        )

        if "algorithm" in search_params:
            md += f"**Algorithm:** {search_params['algorithm']}\n"
            if "SHA-256" in search_params["algorithm"]:
                md += "- *Exact matching: Files must be byte-for-byte identical*\n"
            else:
                md += "- *Similarity matching: Files are considered duplicates based on visual/content similarity*\n"
            md += "\n"

        if "file_types" in search_params:
            md += f"**File Types Processed:** {', '.join(search_params['file_types'])}\n\n"

    # Scan timeframe section
    md += "## Scan Timeframe\n\n"
    md += "*This shows the date range of the files that were analyzed (based on file modification dates).*\n\n"
    if scan_dates:
        md += f"- **Earliest file:** {min(scan_dates).strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"- **Latest file:** {max(scan_dates).strftime('%Y-%m-%d %H:%M:%S')}\n"
        duration = max(scan_dates) - min(scan_dates)
        md += f"- **Time span:** {duration.days} days\n"
    else:
        md += "- No date/time information found in reports\n"
    md += "\n"

    # Directory Analysis section
    md += "## Directory Analysis\n\n"
    md += "*This section breaks down duplicate findings by directory, showing statistics and patterns for each location.*\n\n"

    for d in directories:
        md += f"### 📁 `{d}`\n\n"

        # File counts
        master_count = dir_file_counts.get(d, 0)
        duplicate_count = dir_duplicate_counts.get(d, 0)
        md += "**File Statistics:**\n"
        md += f"- Original files with duplicates: **{master_count}**\n"
        md += f"- Total duplicate instances: **{duplicate_count}**\n"

        if master_count > 0:
            avg_dupes = duplicate_count / master_count
            md += f"- Average duplicates per original: **{avg_dupes:.1f}**\n"
        md += "\n"

        # Confidence score range
        if d in dir_conf_scores:
            min_score, max_score = dir_conf_scores[d]
            md += f"**Confidence Scores:** {min_score:.2f} to {max_score:.2f}\n"
            if min_score == max_score == 1.0:
                md += "- *All matches are exact duplicates (100% confidence)*\n"
            elif min_score >= 0.9:
                md += "- *Very high confidence matches - likely true duplicates*\n"
            elif min_score >= 0.7:
                md += "- *High confidence matches - probably duplicates*\n"
            else:
                md += "- *Mixed confidence levels - manual review recommended*\n"
            md += "\n"

        # Duplicate reasons
        if d in dir_reasons and dir_reasons[d]:
            md += "**Why Files Were Flagged as Duplicates:**\n"
            for reason, pct in sorted(
                dir_reasons[d].items(), key=lambda x: x[1], reverse=True
            ):
                reason_explain = {
                    "hash": "Identical content (same file hash)",
                    "size": "Same file size",
                    "name": "Same or similar filename",
                    "modified": "Same modification date",
                    "same_created_date": "Same creation date",
                    "same_modified_date": "Same modification date",
                    "same_dimensions": "Same image dimensions",
                    "same_camera_make": "Same camera manufacturer",
                    "same_camera_model": "Same camera model",
                    "same_date_taken": "Same photo capture date",
                    "same_iptc_keywords": "Same IPTC keywords",
                    "same_iptc_caption": "Same IPTC caption",
                    "same_xmp_keywords": "Same XMP keywords",
                    "same_xmp_title": "Same XMP title",
                }.get(reason, f"Match criteria: {reason}")

                md += f"- **{pct}%** - {reason_explain}\n"
            md += "\n"

        # File types
        if d in dir_types and dir_types[d]:
            md += f"**File Types:** {', '.join(dir_types[d])}\n"
            md += f"- *{len(dir_types[d])} different file type(s) have duplicates in this directory*\n"
        else:
            md += "**File Types:** None detected\n"

        md += "\n---\n\n"

    # Footer with explanations
    md += "## Understanding This Report\n\n"
    md += "**Confidence Scores:** Indicate how certain the algorithm is that files are duplicates:\n"
    md += "- `1.0` = Exact match (identical content)\n"
    md += "- `0.9-0.99` = Very high similarity (likely duplicates)\n"
    md += "- `0.7-0.89` = High similarity (probably duplicates)\n"
    md += "- `<0.7` = Lower similarity (manual review recommended)\n\n"

    md += "**Duplicate Reasons:** Show why files were identified as duplicates:\n"
    md += "- Multiple criteria can apply to the same file pair\n"
    md += "- Higher percentages indicate more common matching patterns\n"
    md += "- `hash` matches are the most reliable (identical content)\n\n"

    md += "**Next Steps:**\n"
    md += "1. Review high-confidence matches first (score ≥ 0.9)\n"
    md += "2. Use `python main.py --review` for interactive duplicate management\n"
    md += (
        "3. Consider keeping files with better quality, newer dates, or shorter paths\n"
    )
    md += "4. Always backup important files before deletion\n\n"

    md += f"*Report generated by PhotoChomper on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n"

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md)
    return md
