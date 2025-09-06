import csv
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import pandas as pd
from src.config import load_config, log_action
from src.scanner import get_image_metadata, sha256_file, rank_duplicates, HashAlgorithm
import concurrent.futures

# --- Approach Explanation ---
# To ensure metadata extraction does not hang the report generation process (especially on Windows),
# we use concurrent.futures.ThreadPoolExecutor to run get_image_metadata in a separate thread.
# This allows us to specify a timeout for each metadata extraction operation.
# If extraction takes too long (e.g., due to a corrupt or unsupported file), we log a timeout and continue.
# This approach is cross-platform (unlike signal.alarm, which only works on Unix).
# We also add logging at each step for easier debugging and monitoring.

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

    log_action(f"export_report called with {len(dupes)} groups")
    for i, g in enumerate(dupes):
        log_action(f"Group {i+1} has {len(g)} files: {g}")

    metadata_timeout = 10  # seconds

    try:
        for group_id, group in enumerate(dupes):
            log_action(f"Processing duplicate group {group_id+1}/{len(dupes)} with {len(group)} files")
            ranked = rank_duplicates(group, path_preference, filename_preference, quality_ranking)
            log_action(f"Ranked group: {ranked}")
            if not ranked or len(ranked) < 2:
                log_action(f"Skipping group {group_id + 1}: insufficient files or no master")
                continue
            master = ranked[0]
            # Extract metadata for master file with timeout
            master_meta = {}
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(get_image_metadata, master)
                    master_meta = future.result(timeout=metadata_timeout)
                log_action(f"Metadata for master {master}: {master_meta}")
            except concurrent.futures.TimeoutError:
                log_action(f"Timeout extracting metadata for master {master}")
                master_meta = {}
            except Exception as e:
                log_action(f"Error extracting metadata for master {master}: {e}")
                master_meta = {}

            # Prepare duplicate entries
            duplicates = []
            for file_id, file in enumerate(ranked[1:]):
                log_action(f"Processing file {file_id+2}/{len(ranked)}: {file}")
                meta = {}
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(get_image_metadata, file)
                        meta = future.result(timeout=metadata_timeout)
                    log_action(f"Metadata for {file}: {meta}")
                except concurrent.futures.TimeoutError:
                    log_action(f"Timeout extracting metadata for {file}")
                    meta = {}
                except Exception as e:
                    log_action(f"Error extracting metadata for {file}: {e}")
                    meta = {}
                # Example scoring and reasons (customize as needed)
                score = meta.get("quality_score", 0)
                reasons = meta.get("match_reasons", "")
                duplicates.append({
                    "file": file,
                    "name": meta.get("name", ""),
                    "path": meta.get("path", ""),
                    "size": meta.get("size", ""),
                    "created": meta.get("created", ""),
                    "modified": meta.get("modified", ""),
                    "width": meta.get("width", ""),
                    "height": meta.get("height", ""),
                    "file_type": meta.get("file_type", ""),
                    "camera_make": meta.get("camera_make", ""),
                    "camera_model": meta.get("camera_model", ""),
                    "date_taken": meta.get("date_taken", ""),
                    "quality_score": meta.get("quality_score", ""),
                    "iptc_keywords": meta.get("iptc_keywords", ""),
                    "iptc_caption": meta.get("iptc_caption", ""),
                    "xmp_keywords": meta.get("xmp_keywords", ""),
                    "xmp_title": meta.get("xmp_title", ""),
                    "score": score,
                    "reasons": reasons,
                })
                files_processed += 1

            summary.append({
                "group_id": group_id + 1,
                "master": master,
                "master_attributes": {
                    "name": master_meta.get("name", ""),
                    "path": master_meta.get("path", ""),
                    "size": master_meta.get("size", ""),
                    "created": master_meta.get("created", ""),
                    "modified": master_meta.get("modified", ""),
                    "width": master_meta.get("width", ""),
                    "height": master_meta.get("height", ""),
                    "file_type": master_meta.get("file_type", ""),
                    "camera_make": master_meta.get("camera_make", ""),
                    "camera_model": master_meta.get("camera_model", ""),
                    "date_taken": master_meta.get("date_taken", ""),
                    "quality_score": master_meta.get("quality_score", ""),
                    "iptc_keywords": master_meta.get("iptc_keywords", ""),
                    "iptc_caption": master_meta.get("iptc_caption", ""),
                    "xmp_keywords": master_meta.get("xmp_keywords", ""),
                    "xmp_title": master_meta.get("xmp_title", ""),
                },
                "duplicates": duplicates,
            })

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
        "INSERT INTO metadata VALUES (?, ?)", ("total_files", str(sum(len(entry["duplicates"]) for entry in summary)))
    )

    conn.commit()
    conn.close()

    log_action(f"SQLite database created at {db_path} with {len(summary)} groups")

def summarize_reports(report_files, output_file):
    # TODO: Implement summary generation from report files
    return "# Summary not implemented yet\n"
