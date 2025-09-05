import os
import sqlite3
import csv
import hashlib
import concurrent.futures
import platform
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress
from src.config import log_action

# Import optional dependencies for metadata extraction
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    Image = None
    TAGS = None
    GPSTAGS = None

try:
    import iptcinfo3
except ImportError:
    iptcinfo3 = None

try:
    # Skip XMP library on Windows due to Exempi dependency issues
    if platform.system() == "Windows":
        libxmp = None
    else:
        import libxmp
        from libxmp import XMPFiles, XMPMeta
except ImportError:
    libxmp = None

try:
    import exifread
except ImportError:
    exifread = None

console = Console()

@dataclass
class FileRecord:
    """Represents a complete file record with all metadata."""
    datetime_run: str
    file_name: str
    file_path: str
    sha256: str
    dupe_sha256: str
    master: str
    char_length_name: int
    char_length_path: int
    file_size_bytes: int
    file_created_datetime: str
    file_modified_datetime: str
    image_width_px: Optional[int]
    image_height_px: Optional[int]
    file_type: str
    image_camera_make: Optional[str]
    image_camera_model: Optional[str]
    image_datetime_taken: Optional[str]
    image_quality_score: Optional[float]
    image_iptc_keywords: Optional[str]
    image_iptc_caption: Optional[str]
    image_xmp_keywords: Optional[str]
    image_xmp_title: Optional[str]
    image_latitude: Optional[float]
    image_longitude: Optional[float]

def get_file_type(filepath: str) -> str:
    """Determine file type based on extension."""
    extension = Path(filepath).suffix.lower()
    
    # Image types
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw', '.dng'}
    # Video types
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg'}
    # Audio types
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}
    # Document types
    document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'}
    # Archive types
    archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
    
    if extension in image_extensions:
        return "image"
    elif extension in video_extensions:
        return "video"
    elif extension in audio_extensions:
        return "audio"
    elif extension in document_extensions:
        return "document"
    elif extension in archive_extensions:
        return "archive"
    else:
        return "other"

def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of file contents."""
    try:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        log_action(f"Error calculating SHA256 for {filepath}: {e}")
        return ""

def extract_exif_metadata(filepath: str) -> Dict[str, Any]:
    """Extract EXIF metadata from image files."""
    metadata = {}
    
    if not Image or not TAGS:
        return metadata
        
    try:
        with Image.open(filepath) as img:
            # Basic image info
            metadata['width'] = img.width
            metadata['height'] = img.height
            
            # EXIF data
            exif_data = img._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Camera make and model
                    if tag == 'Make':
                        metadata['camera_make'] = str(value).strip()
                    elif tag == 'Model':
                        metadata['camera_model'] = str(value).strip()
                    elif tag == 'DateTime':
                        metadata['datetime_taken'] = str(value)
                    elif tag == 'DateTimeOriginal':
                        metadata['datetime_taken'] = str(value)
                    elif tag == 'GPSInfo' and GPSTAGS:
                        # GPS coordinates
                        gps_data = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = gps_value
                        
                        # Convert GPS coordinates to decimal degrees
                        if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                            lat = gps_data['GPSLatitude']
                            lat_ref = gps_data['GPSLatitudeRef']
                            if lat and len(lat) == 3:
                                decimal_lat = float(lat[0]) + float(lat[1])/60 + float(lat[2])/3600
                                if lat_ref == 'S':
                                    decimal_lat = -decimal_lat
                                metadata['latitude'] = decimal_lat
                        
                        if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                            lon = gps_data['GPSLongitude']
                            lon_ref = gps_data['GPSLongitudeRef']
                            if lon and len(lon) == 3:
                                decimal_lon = float(lon[0]) + float(lon[1])/60 + float(lon[2])/3600
                                if lon_ref == 'W':
                                    decimal_lon = -decimal_lon
                                metadata['longitude'] = decimal_lon
            
            # Calculate simple quality score based on resolution and file size
            if 'width' in metadata and 'height' in metadata:
                file_size = os.path.getsize(filepath)
                pixels = metadata['width'] * metadata['height']
                if pixels > 0:
                    # Quality score: (pixels * file_size) / 1000000 for normalization
                    metadata['quality_score'] = (pixels * file_size) / 1000000.0
                    
    except Exception as e:
        log_action(f"Error extracting EXIF from {filepath}: {e}")
    
    return metadata

def extract_iptc_metadata(filepath: str) -> Dict[str, Any]:
    """Extract IPTC metadata from image files."""
    metadata = {}
    
    if not iptcinfo3:
        return metadata
        
    try:
        info = iptcinfo3.IPTCInfo(filepath)
        if info:
            keywords = info.get('keywords', [])
            if keywords:
                metadata['iptc_keywords'] = ', '.join([k.decode('utf-8') if isinstance(k, bytes) else str(k) for k in keywords])
            
            caption = info.get('caption/abstract')
            if caption:
                if isinstance(caption, bytes):
                    caption = caption.decode('utf-8')
                metadata['iptc_caption'] = str(caption)
                
    except Exception as e:
        log_action(f"Error extracting IPTC from {filepath}: {e}")
    
    return metadata

def extract_xmp_metadata(filepath: str) -> Dict[str, Any]:
    """Extract XMP metadata from image files."""
    metadata = {}
    
    if not libxmp:
        return metadata
        
    try:
        xmpfile = XMPFiles(file_path=filepath, open_forupdate=False)
        xmp = xmpfile.get_xmp()
        if xmp:
            # Try to get common XMP properties
            try:
                # Keywords
                keywords_prop = xmp.get_property('http://purl.org/dc/elements/1.1/', 'subject')
                if keywords_prop:
                    metadata['xmp_keywords'] = str(keywords_prop)
            except:
                pass
                
            try:
                # Title
                title_prop = xmp.get_property('http://purl.org/dc/elements/1.1/', 'title')
                if title_prop:
                    metadata['xmp_title'] = str(title_prop)
            except:
                pass
                
        xmpfile.close_file()
        
    except Exception as e:
        log_action(f"Error extracting XMP from {filepath}: {e}")
    
    return metadata

def extract_comprehensive_metadata(filepath: str, run_datetime: str) -> FileRecord:
    """Extract all available metadata from a file."""
    file_path_obj = Path(filepath)
    
    # Basic file system metadata
    try:
        stat = file_path_obj.stat()
        file_size = stat.st_size
        created_time = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
    except Exception as e:
        log_action(f"Error getting file stats for {filepath}: {e}")
        file_size = 0
        created_time = ""
        modified_time = ""
    
    # Initialize metadata fields
    width = None
    height = None
    camera_make = None
    camera_model = None
    datetime_taken = None
    quality_score = None
    iptc_keywords = None
    iptc_caption = None
    xmp_keywords = None
    xmp_title = None
    latitude = None
    longitude = None
    
    # File type detection
    file_type = get_file_type(filepath)
    
    # Extract metadata for image files
    if file_type == "image":
        try:
            # EXIF metadata
            exif_metadata = extract_exif_metadata(filepath)
            width = exif_metadata.get('width')
            height = exif_metadata.get('height')
            camera_make = exif_metadata.get('camera_make')
            camera_model = exif_metadata.get('camera_model')
            datetime_taken = exif_metadata.get('datetime_taken')
            quality_score = exif_metadata.get('quality_score')
            latitude = exif_metadata.get('latitude')
            longitude = exif_metadata.get('longitude')
            
            # IPTC metadata
            iptc_metadata = extract_iptc_metadata(filepath)
            iptc_keywords = iptc_metadata.get('iptc_keywords')
            iptc_caption = iptc_metadata.get('iptc_caption')
            
            # XMP metadata
            xmp_metadata = extract_xmp_metadata(filepath)
            xmp_keywords = xmp_metadata.get('xmp_keywords')
            xmp_title = xmp_metadata.get('xmp_title')
            
        except Exception as e:
            log_action(f"Error extracting image metadata from {filepath}: {e}")
    
    # Calculate SHA256 hash
    sha256_hash = calculate_sha256(filepath)
    
    # File name and character lengths
    filename = file_path_obj.name
    char_length_name = len(filename)
    char_length_path = len(filepath)
    
    return FileRecord(
        datetime_run=run_datetime,
        file_name=filename,
        file_path=filepath,
        sha256=sha256_hash,
        dupe_sha256="No",  # Will be updated after all files are processed
        master="No",  # Will be updated after all files are processed
        char_length_name=char_length_name,
        char_length_path=char_length_path,
        file_size_bytes=file_size,
        file_created_datetime=created_time,
        file_modified_datetime=modified_time,
        image_width_px=width,
        image_height_px=height,
        file_type=file_type,
        image_camera_make=camera_make,
        image_camera_model=camera_model,
        image_datetime_taken=datetime_taken,
        image_quality_score=quality_score,
        image_iptc_keywords=iptc_keywords,
        image_iptc_caption=iptc_caption,
        image_xmp_keywords=xmp_keywords,
        image_xmp_title=xmp_title,
        image_latitude=latitude,
        image_longitude=longitude
    )

def discover_all_files(search_dir: str, excluded_extensions: List[str]) -> Iterator[str]:
    """Discover all files in directory tree, including hidden files."""
    search_path = Path(search_dir)
    excluded_ext_set = {f".{ext.lower()}" for ext in excluded_extensions}
    
    try:
        for item in search_path.rglob("*"):
            if item.is_file():
                # Check if extension should be excluded
                if excluded_ext_set and item.suffix.lower() in excluded_ext_set:
                    continue
                yield str(item)
    except Exception as e:
        log_action(f"Error scanning directory {search_dir}: {e}")
        console.print(f"[red]Error scanning directory {search_dir}: {e}[/red]")

def create_sqlite_database(db_path: str) -> sqlite3.Connection:
    """Create SQLite database and table for file records."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime_run TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            sha256 TEXT,
            dupe_sha256 TEXT,
            master TEXT,
            char_length_name INTEGER,
            char_length_path INTEGER,
            file_size_bytes INTEGER,
            file_created_datetime TEXT,
            file_modified_datetime TEXT,
            image_width_px INTEGER,
            image_height_px INTEGER,
            file_type TEXT,
            image_camera_make TEXT,
            image_camera_model TEXT,
            image_datetime_taken TEXT,
            image_quality_score REAL,
            image_iptc_keywords TEXT,
            image_iptc_caption TEXT,
            image_xmp_keywords TEXT,
            image_xmp_title TEXT,
            image_latitude REAL,
            image_longitude REAL,
            UNIQUE(datetime_run, file_path)
        )
    ''')
    
    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_datetime_run ON file_records(datetime_run)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_path ON file_records(file_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sha256 ON file_records(sha256)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_type ON file_records(file_type)')
    
    conn.commit()
    return conn

def insert_record_to_sqlite(conn: sqlite3.Connection, record: FileRecord):
    """Insert a file record into SQLite database."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO file_records 
        (datetime_run, file_name, file_path, sha256, dupe_sha256, master, char_length_name, char_length_path,
         file_size_bytes, file_created_datetime, file_modified_datetime, image_width_px,
         image_height_px, file_type, image_camera_make, image_camera_model, image_datetime_taken,
         image_quality_score, image_iptc_keywords, image_iptc_caption, image_xmp_keywords,
         image_xmp_title, image_latitude, image_longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record.datetime_run, record.file_name, record.file_path, record.sha256, record.dupe_sha256,
        record.master, record.char_length_name, record.char_length_path, record.file_size_bytes,
        record.file_created_datetime, record.file_modified_datetime, record.image_width_px,
        record.image_height_px, record.file_type, record.image_camera_make, record.image_camera_model,
        record.image_datetime_taken, record.image_quality_score, record.image_iptc_keywords,
        record.image_iptc_caption, record.image_xmp_keywords, record.image_xmp_title,
        record.image_latitude, record.image_longitude
    ))

def write_csv_header(csv_writer):
    """Write CSV header row."""
    csv_writer.writerow([
        'DateTimeRun', 'FileName', 'FilePath', 'SHA256', 'DupeSHA256', 'Master', 'CharLengthName', 'CharLengthPath',
        'FileSizeBytes', 'FileCreatedDateTime', 'FileModifiedDateTime', 'ImageWidthPx', 'ImageHeightPx',
        'FileType', 'ImageCameraMake', 'ImageCameraModel', 'ImageDateTimeTaken', 'ImageQualityScore',
        'ImageIPTCKeywords', 'ImageIPTCCaption', 'ImageXMPKeywords', 'ImageXMPTitle',
        'ImageLatitude', 'ImageLongitude'
    ])

def write_csv_record(csv_writer, record: FileRecord):
    """Write a file record to CSV."""
    csv_writer.writerow([
        record.datetime_run, record.file_name, record.file_path, record.sha256, record.dupe_sha256,
        record.master, record.char_length_name, record.char_length_path, record.file_size_bytes,
        record.file_created_datetime, record.file_modified_datetime, record.image_width_px,
        record.image_height_px, record.file_type, record.image_camera_make, record.image_camera_model,
        record.image_datetime_taken, record.image_quality_score, record.image_iptc_keywords,
        record.image_iptc_caption, record.image_xmp_keywords, record.image_xmp_title,
        record.image_latitude, record.image_longitude
    ])

def detect_duplicate_sha256(records: List[FileRecord]) -> None:
    """Mark records with duplicate SHA256 values."""
    # Count occurrences of each SHA256 hash
    sha256_counts = {}
    for record in records:
        if record.sha256:  # Only count non-empty hashes
            sha256_counts[record.sha256] = sha256_counts.get(record.sha256, 0) + 1
    
    # Mark duplicates
    for record in records:
        if record.sha256 and sha256_counts.get(record.sha256, 0) > 1:
            record.dupe_sha256 = "Yes"
        else:
            record.dupe_sha256 = "No"

def determine_master_files(records: List[FileRecord]) -> None:
    """Determine master file for each SHA256 group based on sorting criteria."""
    # Group records by SHA256 hash
    sha256_groups = {}
    for record in records:
        if record.sha256:  # Only process records with valid SHA256
            if record.sha256 not in sha256_groups:
                sha256_groups[record.sha256] = []
            sha256_groups[record.sha256].append(record)
    
    # For each group, determine the master file
    for sha256_hash, group_records in sha256_groups.items():
        if len(group_records) == 1:
            # Single file - it's the master
            group_records[0].master = "Yes"
        else:
            # Multiple files with same SHA256 - sort to find master
            # Filter out files with "zip" in the name first
            eligible_records = [r for r in group_records if "zip" not in r.file_name.lower()]
            
            # If all files have "zip" in name, use all files
            if not eligible_records:
                eligible_records = group_records
            
            # Sort by CharLengthName (ascending) then CharLengthPath (ascending)
            eligible_records.sort(key=lambda r: (r.char_length_name, r.char_length_path))
            
            # Mark the first one as master, others as not master
            for i, record in enumerate(group_records):
                if record == eligible_records[0]:
                    record.master = "Yes"
                else:
                    record.master = "No"

def process_file_batch(file_paths: List[str], run_datetime: str) -> List[FileRecord]:
    """Process a batch of files and extract metadata."""
    records = []
    for filepath in file_paths:
        try:
            record = extract_comprehensive_metadata(filepath, run_datetime)
            records.append(record)
        except Exception as e:
            log_action(f"Error processing file {filepath}: {e}")
            console.print(f"[red]Error processing {filepath}: {e}[/red]")
    return records

def run_comprehensive_listing(search_dir: str, output_dir: str, excluded_extensions: List[str]):
    """Run comprehensive file listing with metadata extraction."""
    run_datetime = datetime.now().isoformat()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Output file paths
    csv_path = Path(output_dir) / f"file_listing_{timestamp}.csv"
    sqlite_path = Path(output_dir) / f"file_listing_{timestamp}.db"
    
    console.print("[bold blue]📋 Starting comprehensive file listing...[/bold blue]")
    console.print(f"• Search directory: [cyan]{search_dir}[/cyan]")
    console.print(f"• Output CSV: [cyan]{csv_path}[/cyan]")
    console.print(f"• Output SQLite: [cyan]{sqlite_path}[/cyan]")
    
    # Discover all files first to get total count
    console.print("[yellow]Discovering files...[/yellow]")
    all_files = list(discover_all_files(search_dir, excluded_extensions))
    total_files = len(all_files)
    
    if total_files == 0:
        console.print("[red]No files found in the specified directory.[/red]")
        return
    
    console.print(f"[green]Found {total_files:,} files to process[/green]")
    
    # Initialize output files
    sqlite_conn = create_sqlite_database(str(sqlite_path))
    csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
    csv_writer = csv.writer(csv_file)
    write_csv_header(csv_writer)
    
    # Process files with progress tracking - first collect all records
    batch_size = 100  # Process files in batches for better memory management
    processed_count = 0
    all_records = []
    
    try:
        with Progress() as progress:
            task = progress.add_task("Processing files...", total=total_files)
            
            # Process files in batches using thread pool - collect records first
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                for i in range(0, total_files, batch_size):
                    batch_files = all_files[i:i + batch_size]
                    
                    # Submit batch for processing
                    future = executor.submit(process_file_batch, batch_files, run_datetime)
                    records = future.result()
                    
                    # Collect all records
                    all_records.extend(records)
                    processed_count += len(records)
                    progress.update(task, completed=processed_count)
        
        # Detect duplicate SHA256 values across all files
        console.print("[yellow]Detecting duplicate SHA256 values...[/yellow]")
        detect_duplicate_sha256(all_records)
        
        # Determine master files for each SHA256 group
        console.print("[yellow]Determining master files...[/yellow]")
        determine_master_files(all_records)
        
        # Count duplicates and masters for reporting
        duplicate_count = sum(1 for record in all_records if record.dupe_sha256 == "Yes")
        master_count = sum(1 for record in all_records if record.master == "Yes")
        console.print(f"[cyan]Found {duplicate_count} files with duplicate SHA256 values[/cyan]")
        console.print(f"[cyan]Identified {master_count} master files[/cyan]")
        
        # Now write all records to outputs
        console.print("[yellow]Writing output files...[/yellow]")
        with Progress() as progress:
            write_task = progress.add_task("Writing outputs...", total=len(all_records))
            
            for i, record in enumerate(all_records):
                # Write to CSV
                write_csv_record(csv_writer, record)
                
                # Write to SQLite
                insert_record_to_sqlite(sqlite_conn, record)
                
                # Update progress every 100 records for performance
                if i % 100 == 0 or i == len(all_records) - 1:
                    progress.update(write_task, completed=i + 1)
                    # Commit SQLite batch
                    sqlite_conn.commit()
                    # Flush CSV
                    csv_file.flush()
    
    finally:
        # Close files
        csv_file.close()
        sqlite_conn.close()
    
    # Final statistics
    console.print("\n[bold green]✅ File listing completed![/bold green]")
    console.print(f"• Processed files: [cyan]{processed_count:,}[/cyan]")
    console.print(f"• CSV output: [cyan]{csv_path}[/cyan]")
    console.print(f"• SQLite output: [cyan]{sqlite_path}[/cyan]")
    console.print(f"• Run timestamp: [cyan]{run_datetime}[/cyan]")
    
    # Log completion
    log_action(f"File listing completed: {processed_count} files processed | Search: {search_dir} | Output: {output_dir}")