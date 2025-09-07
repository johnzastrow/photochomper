"""
Clean, simple report generation module.
Refactored for clarity and debuggability.
"""
import csv
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

from src.config import load_config, log_action
from src.scanner import get_image_metadata, sha256_file, rank_duplicates, HashAlgorithm


def safe_get_metadata(filepath: str) -> Dict:
    """
    Ultra-safe metadata extraction that never hangs.
    Only uses basic file system operations.
    """
    log_action(f"Getting basic metadata for: {filepath}")
    
    try:
        # Get basic file stats - this should never hang
        stat_info = os.stat(filepath)
        file_size = stat_info.st_size
        modified_time = time.ctime(stat_info.st_mtime)
        created_time = time.ctime(stat_info.st_ctime)
        
        # Basic file info
        name = os.path.basename(filepath)
        file_ext = os.path.splitext(name)[1].lower()
        
        # Simple file type detection
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
        
        if file_ext in image_extensions:
            file_type = "IMAGE"
        elif file_ext in video_extensions:
            file_type = "VIDEO"
        else:
            file_type = "OTHER"
        
        metadata = {
            "name": name,
            "path": filepath,
            "size": file_size,
            "created": created_time,
            "modified": modified_time,
            "width": 0,  # Not extracting image dimensions to avoid hanging
            "height": 0,
            "file_type": file_type,
            "camera_make": "",
            "camera_model": "",
            "date_taken": modified_time,  # Use file modification as fallback
            "quality_score": 0,
            "iptc_keywords": [],
            "iptc_caption": "",
            "xmp_keywords": [],
            "xmp_title": "",
        }
        
        log_action(f"Successfully extracted basic metadata for: {name} ({file_size} bytes)")
        return metadata
        
    except Exception as e:
        log_action(f"Error getting file stats for {filepath}: {e}")
        # Return absolute minimal metadata
        return {
            "name": os.path.basename(filepath) if filepath else "unknown",
            "path": filepath,
            "size": 0,
            "created": "",
            "modified": "",
            "width": 0,
            "height": 0,
            "file_type": "UNKNOWN",
            "camera_make": "",
            "camera_model": "",
            "date_taken": "",
            "quality_score": 0,
            "iptc_keywords": [],
            "iptc_caption": "",
            "xmp_keywords": [],
            "xmp_title": "",
        }


def process_single_group(group_id: int, group: List[str], total_groups: int) -> Dict:
    """
    Process a single duplicate group.
    Returns a dictionary with group data or None if group should be skipped.
    """
    log_action(f"=== Processing group {group_id + 1}/{total_groups} ===")
    log_action(f"Group contains {len(group)} files: {group}")
    
    if len(group) < 2:
        log_action(f"Skipping group {group_id + 1}: insufficient files (need 2+, got {len(group)})")
        return None
    
    # Simple ranking: largest file first, then newest
    log_action("Ranking files to determine master...")
    try:
        ranked_files = []
        for filepath in group:
            try:
                stat = os.stat(filepath)
                ranked_files.append((filepath, stat.st_size, stat.st_mtime))
                log_action(f"File stats: {filepath} - size: {stat.st_size}, mtime: {stat.st_mtime}")
            except OSError as e:
                log_action(f"Could not stat file {filepath}: {e}")
                # Add with minimal info if stat fails
                ranked_files.append((filepath, 0, 0))
        
        # Sort by size (descending) then by modification time (descending)
        ranked_files.sort(key=lambda x: (-x[1], -x[2]))
        ranked = [f[0] for f in ranked_files]
        log_action(f"Ranked files: {ranked}")
    except Exception as e:
        log_action(f"Error ranking files in group {group_id + 1}: {e}")
        return None
    
    master = ranked[0]
    duplicates = ranked[1:]
    
    log_action(f"Master file: {master}")
    log_action(f"Duplicate files: {duplicates}")
    
    # Get metadata for master
    log_action("Getting master file metadata...")
    master_meta = safe_get_metadata(master)
    
    # Process each duplicate
    duplicate_entries = []
    for i, dup_file in enumerate(duplicates):
        log_action(f"Processing duplicate {i + 1}/{len(duplicates)}: {dup_file}")
        dup_meta = safe_get_metadata(dup_file)
        
        # Create duplicate entry
        duplicate_entry = {
            "file": dup_file,
            "score": 0.95,  # Simple fixed score for now
            "reasons": "duplicate_detected",
            "name": dup_meta.get("name", ""),
            "path": dup_meta.get("path", ""),
            "size": dup_meta.get("size", ""),
            "created": dup_meta.get("created", ""),
            "modified": dup_meta.get("modified", ""),
            "width": dup_meta.get("width", ""),
            "height": dup_meta.get("height", ""),
            "file_type": dup_meta.get("file_type", ""),
            "camera_make": dup_meta.get("camera_make", ""),
            "camera_model": dup_meta.get("camera_model", ""),
            "date_taken": dup_meta.get("date_taken", ""),
            "quality_score": dup_meta.get("quality_score", ""),
            "iptc_keywords": dup_meta.get("iptc_keywords", ""),
            "iptc_caption": dup_meta.get("iptc_caption", ""),
            "xmp_keywords": dup_meta.get("xmp_keywords", ""),
            "xmp_title": dup_meta.get("xmp_title", ""),
        }
        duplicate_entries.append(duplicate_entry)
        log_action(f"Added duplicate entry for: {dup_file}")
    
    # Create group entry
    group_entry = {
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
        "duplicates": duplicate_entries,
    }
    
    log_action(f"Completed processing group {group_id + 1}")
    return group_entry


def export_report(
    dupes: List[List[str]],
    formats: List[str] = ["csv", "json"],
    out_prefix: str = None,
    config_path: str = None,
    exec_time: float = None,
    progress_callback=None,
):
    """
    Clean, simple report export function.
    """
    log_action("=== STARTING REPORT GENERATION ===")
    log_action(f"Input: {len(dupes)} groups with total files: {sum(len(g) for g in dupes)}")
    log_action(f"Output formats: {formats}")
    log_action(f"Output prefix: {out_prefix}")
    
    # Set up output path
    if out_prefix is None:
        out_prefix = os.path.join(os.getcwd(), "duplicates_report")
    
    # Process each group
    summary = []
    total_files_processed = 0
    total_files = sum(len(group) for group in dupes)
    
    log_action(f"Will process {len(dupes)} groups containing {total_files} total files")
    
    try:
        for group_id, group in enumerate(dupes):
            log_action(f"\n--- Starting group {group_id + 1}/{len(dupes)} ---")
            
            group_entry = process_single_group(group_id, group, len(dupes))
            
            if group_entry is not None:
                summary.append(group_entry)
                files_in_group = len(group)
                total_files_processed += files_in_group
                
                log_action(f"Group {group_id + 1} processed successfully. Files: {files_in_group}")
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(total_files_processed)
                    log_action(f"Progress callback called: {total_files_processed}/{total_files}")
            else:
                log_action(f"Group {group_id + 1} was skipped")
            
            log_action(f"--- Finished group {group_id + 1}/{len(dupes)} ---\n")
    
    except KeyboardInterrupt:
        log_action(f"Report generation interrupted by user. Processed {total_files_processed}/{total_files} files.")
        print(f"\n⚠️  Report generation interrupted. Processed {total_files_processed}/{total_files} files.")
        print("Partial report data will be saved with completed entries.")
    
    log_action(f"Report processing complete. Generated {len(summary)} group entries.")
    
    # Write CSV output
    if "csv" in formats:
        log_action("Writing CSV output...")
        write_csv_report(summary, f"{out_prefix}.csv")
    
    # Write JSON output  
    if "json" in formats:
        log_action("Writing JSON output...")
        write_json_report(summary, f"{out_prefix}.json")
    
    # Write SQLite output
    if "sqlite" in formats:
        log_action("Writing SQLite output...")
        write_sqlite_report(summary, f"{out_prefix}.db")
    
    log_action(f"=== REPORT GENERATION COMPLETE ===")
    log_action(f"Processed {len(summary)} groups, {total_files_processed} files")
    log_action(f"Output files written with prefix: {out_prefix}")


def write_csv_report(summary: List[Dict], csv_path: str):
    """Write CSV report."""
    log_action(f"Writing CSV to: {csv_path}")
    
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                "GroupID", "Master", "File", "Name", "Size", "Created", "Modified",
                "Width", "Height", "FileType", "CameraMake", "CameraModel", 
                "DateTaken", "QualityScore", "Score", "Reasons"
            ])
            
            # Write data
            for entry in summary:
                group_id = entry["group_id"]
                master = entry["master"]
                
                # Write master row
                master_attrs = entry["master_attributes"]
                writer.writerow([
                    group_id, "Yes", master, master_attrs.get("name", ""),
                    master_attrs.get("size", ""), master_attrs.get("created", ""),
                    master_attrs.get("modified", ""), master_attrs.get("width", ""),
                    master_attrs.get("height", ""), master_attrs.get("file_type", ""),
                    master_attrs.get("camera_make", ""), master_attrs.get("camera_model", ""),
                    master_attrs.get("date_taken", ""), master_attrs.get("quality_score", ""),
                    "", "master"
                ])
                
                # Write duplicate rows
                for dup in entry["duplicates"]:
                    writer.writerow([
                        group_id, "", dup["file"], dup.get("name", ""),
                        dup.get("size", ""), dup.get("created", ""), dup.get("modified", ""),
                        dup.get("width", ""), dup.get("height", ""), dup.get("file_type", ""),
                        dup.get("camera_make", ""), dup.get("camera_model", ""),
                        dup.get("date_taken", ""), dup.get("quality_score", ""),
                        dup.get("score", ""), dup.get("reasons", "")
                    ])
        
        log_action(f"Successfully wrote CSV with {len(summary)} groups")
    
    except Exception as e:
        log_action(f"Error writing CSV: {e}")


def write_json_report(summary: List[Dict], json_path: str):
    """Write JSON report."""
    log_action(f"Writing JSON to: {json_path}")
    
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        
        log_action(f"Successfully wrote JSON with {len(summary)} groups")
    
    except Exception as e:
        log_action(f"Error writing JSON: {e}")


def write_sqlite_report(summary: List[Dict], db_path: str):
    """Write SQLite report."""
    log_action(f"Writing SQLite to: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                master TEXT,
                file TEXT,
                name TEXT,
                size INTEGER,
                created TEXT,
                modified TEXT,
                width INTEGER,
                height INTEGER,
                file_type TEXT,
                camera_make TEXT,
                camera_model TEXT,
                date_taken TEXT,
                quality_score REAL,
                score REAL,
                reasons TEXT
            )
        """)
        
        # Insert data
        for entry in summary:
            group_id = entry["group_id"]
            master = entry["master"]
            master_attrs = entry["master_attributes"]
            
            # Insert master
            cursor.execute("""
                INSERT INTO duplicates (
                    group_id, master, file, name, size, created, modified,
                    width, height, file_type, camera_make, camera_model,
                    date_taken, quality_score, score, reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                group_id, "Yes", master, master_attrs.get("name", ""),
                master_attrs.get("size", 0), master_attrs.get("created", ""),
                master_attrs.get("modified", ""), master_attrs.get("width", 0),
                master_attrs.get("height", 0), master_attrs.get("file_type", ""),
                master_attrs.get("camera_make", ""), master_attrs.get("camera_model", ""),
                master_attrs.get("date_taken", ""), master_attrs.get("quality_score", 0),
                0, "master"
            ))
            
            # Insert duplicates
            for dup in entry["duplicates"]:
                cursor.execute("""
                    INSERT INTO duplicates (
                        group_id, master, file, name, size, created, modified,
                        width, height, file_type, camera_make, camera_model,
                        date_taken, quality_score, score, reasons
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    group_id, "", dup["file"], dup.get("name", ""),
                    dup.get("size", 0), dup.get("created", ""), dup.get("modified", ""),
                    dup.get("width", 0), dup.get("height", 0), dup.get("file_type", ""),
                    dup.get("camera_make", ""), dup.get("camera_model", ""),
                    dup.get("date_taken", ""), dup.get("quality_score", 0),
                    dup.get("score", 0), dup.get("reasons", "")
                ))
        
        conn.commit()
        conn.close()
        
        log_action(f"Successfully wrote SQLite with {len(summary)} groups")
    
    except Exception as e:
        log_action(f"Error writing SQLite: {e}")


def summarize_reports(report_files, output_file):
    """Generate summary from report files."""
    return "# Summary not implemented yet\n"