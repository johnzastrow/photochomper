import os
import hashlib
import concurrent.futures
import gc
import sqlite3
import json
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Iterator, Generator
from enum import Enum
from dataclasses import dataclass
from src.config import log_action

# Optional dependencies
try:
    import psutil
except ImportError:
    psutil = None

# Image processing imports
try:
    from PIL import Image
    import imagehash
except ImportError:
    Image = None
    imagehash = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import ffmpeg
except ImportError:
    ffmpeg = None

try:
    import iptcinfo3
except ImportError:
    iptcinfo3 = None

try:
    # Skip XMP library on Windows due to Exempi dependency issues
    if platform.system() == "Windows":
        libxmp = None
        log_action("Skipping XMP metadata extraction on Windows (Exempi library not available)")
    else:
        import libxmp
        from libxmp import XMPFiles, XMPMeta
except ImportError:
    libxmp = None

try:
    import exifread
except ImportError:
    exifread = None

BACKUP_DIR = "photochomper_backup"
HASH_CACHE_DB = "photochomper_hash_cache.db"

class HashAlgorithm(Enum):
    """Supported hash algorithms for duplicate detection."""
    SHA256 = "sha256"          # Exact content hash
    DHASH = "dhash"            # Difference hash (perceptual)
    PHASH = "phash"            # Perceptual hash
    AHASH = "ahash"            # Average hash
    WHASH = "whash"            # Wavelet hash

class FileType(Enum):
    """Supported file types."""
    IMAGE = "image"
    VIDEO = "video"
    UNKNOWN = "unknown"

@dataclass
class HashResult:
    """Container for hash computation results."""
    algorithm: HashAlgorithm
    hash_value: str
    file_path: str
    file_type: FileType
    sha256_hash: str = ""  # Always calculated SHA256 hash
    similarity_score: float = 0.0  # Similarity score for comparison
    error: Optional[str] = None

class HashCache:
    """Memory-efficient SQLite-based hash cache to avoid recomputing unchanged files."""
    
    def __init__(self, cache_file: str = HASH_CACHE_DB):
        self.cache_file = cache_file
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for hash caching."""
        try:
            self.conn = sqlite3.connect(self.cache_file)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS hash_cache (
                    filepath TEXT PRIMARY KEY,
                    file_size INTEGER,
                    file_mtime REAL,
                    algorithm TEXT,
                    sha256_hash TEXT,
                    perceptual_hash TEXT,
                    cached_at REAL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON hash_cache(filepath)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_algorithm ON hash_cache(algorithm)")
            self.conn.commit()
            log_action(f"Hash cache initialized: {self.cache_file}")
        except Exception as e:
            log_action(f"Error initializing hash cache: {e}")
            self.conn = None
    
    def get_cached_hash(self, filepath: str, algorithm: HashAlgorithm) -> Optional[HashResult]:
        """Retrieve cached hash if file hasn't changed."""
        if not self.conn:
            return None
        
        try:
            # Get current file stats
            stat = os.stat(filepath)
            file_size = stat.st_size
            file_mtime = stat.st_mtime
            
            # Query cache
            cursor = self.conn.execute("""
                SELECT sha256_hash, perceptual_hash, file_size, file_mtime 
                FROM hash_cache 
                WHERE filepath = ? AND algorithm = ?
            """, (filepath, algorithm.value))
            
            row = cursor.fetchone()
            if row:
                cached_sha256, cached_perceptual, cached_size, cached_mtime = row
                
                # Check if file has changed
                if cached_size == file_size and abs(cached_mtime - file_mtime) < 1.0:
                    # File unchanged, return cached result
                    return HashResult(
                        algorithm=algorithm,
                        hash_value=cached_perceptual or "",
                        file_path=filepath,
                        file_type=get_file_type(filepath),
                        sha256_hash=cached_sha256 or "",
                        similarity_score=0.0
                    )
        except Exception as e:
            log_action(f"Error retrieving cached hash for {filepath}: {e}")
        
        return None
    
    def cache_hash(self, result: HashResult):
        """Store hash result in cache."""
        if not self.conn or not result.file_path:
            return
        
        try:
            stat = os.stat(result.file_path)
            import time
            
            self.conn.execute("""
                INSERT OR REPLACE INTO hash_cache 
                (filepath, file_size, file_mtime, algorithm, sha256_hash, perceptual_hash, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.file_path,
                stat.st_size,
                stat.st_mtime,
                result.algorithm.value,
                result.sha256_hash,
                result.hash_value,
                time.time()
            ))
            self.conn.commit()
        except Exception as e:
            log_action(f"Error caching hash for {result.file_path}: {e}")
    
    def cleanup_old_entries(self, days_old: int = 30):
        """Remove cache entries for files older than specified days."""
        if not self.conn:
            return
        
        try:
            import time
            cutoff_time = time.time() - (days_old * 24 * 3600)
            
            cursor = self.conn.execute("DELETE FROM hash_cache WHERE cached_at < ?", (cutoff_time,))
            deleted = cursor.rowcount
            self.conn.commit()
            
            if deleted > 0:
                log_action(f"Cleaned up {deleted} old cache entries")
        except Exception as e:
            log_action(f"Error cleaning up cache: {e}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

@dataclass
class SimilarityMatch:
    """Container for similarity comparison results."""
    file1: str
    file2: str
    algorithm: HashAlgorithm
    similarity_score: float
    hash1: str
    hash2: str

@dataclass
class MemoryStats:
    """Memory usage statistics."""
    available_mb: float
    used_mb: float
    percent_used: float
    
    @classmethod
    def current(cls) -> 'MemoryStats':
        """Get current memory statistics."""
        if psutil:
            memory = psutil.virtual_memory()
            return cls(
                available_mb=memory.available / (1024 * 1024),
                used_mb=memory.used / (1024 * 1024),
                percent_used=memory.percent
            )
        else:
            # Fallback when psutil is not available
            import resource
            try:
                # Use resource module for basic memory info (Unix only)
                usage = resource.getrusage(resource.RUSAGE_SELF)
                used_mb = usage.ru_maxrss / 1024  # Convert KB to MB
                return cls(
                    available_mb=2048.0,  # Assume 2GB available (conservative)
                    used_mb=used_mb,
                    percent_used=min(used_mb / 2048.0 * 100, 100.0)
                )
            except Exception:
                # Ultimate fallback
                return cls(
                    available_mb=2048.0,
                    used_mb=512.0,  # Conservative estimate
                    percent_used=25.0
                )

def get_optimal_chunk_size(total_files: int, available_memory_mb: float = None) -> int:
    """Calculate optimal chunk size based on available memory and file count."""
    if available_memory_mb is None:
        memory_stats = MemoryStats.current()
        available_memory_mb = memory_stats.available_mb
    
    # Conservative memory usage - use at most 25% of available memory
    usable_memory_mb = available_memory_mb * 0.25
    
    # Estimate memory per file (hash + metadata + overhead)
    estimated_memory_per_file_kb = 10  # Conservative estimate
    max_files_in_memory = int((usable_memory_mb * 1024) / estimated_memory_per_file_kb)
    
    # Choose chunk size based on constraints
    if total_files <= max_files_in_memory:
        # All files fit in memory, process in single chunk
        return total_files
    else:
        # Need to chunk, but ensure reasonable minimum chunk size
        chunk_size = max(min(max_files_in_memory, 1000), 100)
        log_action(f"Memory optimization: Processing {total_files} files in chunks of {chunk_size}")
        return chunk_size

def scan_files_chunked(dirs: List[str], types: List[str], exclude_dirs: List[str], 
                      chunk_size: int = None) -> Generator[List[str], None, None]:
    """Scan files in chunks to optimize memory usage for large collections."""
    all_files = []
    
    # First pass: collect all file paths
    for d in dirs:
        if not os.path.exists(d):
            log_action(f"Directory not found: {d}")
            continue
            
        for root, _, filenames in os.walk(d):
            if any(ex in root for ex in exclude_dirs):
                continue
            for fname in filenames:
                if is_supported_file(fname, types):
                    all_files.append(os.path.join(root, fname))
    
    if not all_files:
        return
    
    # Determine chunk size if not provided
    if chunk_size is None:
        chunk_size = get_optimal_chunk_size(len(all_files))
    
    log_action(f"Scanning {len(all_files)} files in chunks of {chunk_size}")
    
    # Yield chunks of files
    for i in range(0, len(all_files), chunk_size):
        chunk = all_files[i:i + chunk_size]
        yield chunk
        
        # Force garbage collection between chunks to free memory
        if i + chunk_size < len(all_files):  # Not the last chunk
            gc.collect()

def sha256_file(filepath: str) -> str:
    """Compute SHA-256 hash of a file for exact duplicate detection."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log_action(f"Error hashing file {filepath}: {e}")
        return ""

def compute_perceptual_hash(filepath: str, algorithm: HashAlgorithm = HashAlgorithm.DHASH, hash_size: int = 8, 
                          cache: Optional[HashCache] = None) -> HashResult:
    """Compute perceptual hash of an image file with optional caching."""
    if not Image or not imagehash:
        return HashResult(algorithm, "", filepath, FileType.IMAGE, "", 0.0, "PIL/imagehash not available")
    
    # Check cache first
    if cache:
        cached_result = cache.get_cached_hash(filepath, algorithm)
        if cached_result:
            return cached_result
    
    try:
        # Always calculate SHA256 first
        sha256_hash = sha256_file(filepath)
        
        with Image.open(filepath) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Compute hash based on algorithm
            if algorithm == HashAlgorithm.DHASH:
                hash_obj = imagehash.dhash(img, hash_size=hash_size)
            elif algorithm == HashAlgorithm.PHASH:
                hash_obj = imagehash.phash(img, hash_size=hash_size)
            elif algorithm == HashAlgorithm.AHASH:
                hash_obj = imagehash.average_hash(img, hash_size=hash_size)
            elif algorithm == HashAlgorithm.WHASH:
                hash_obj = imagehash.whash(img, hash_size=hash_size)
            else:
                return HashResult(algorithm, "", filepath, FileType.IMAGE, sha256_hash, 0.0, f"Unsupported algorithm: {algorithm}")
            
            result = HashResult(algorithm, str(hash_obj), filepath, FileType.IMAGE, sha256_hash, 0.0)
            
            # Cache the result
            if cache:
                cache.cache_hash(result)
            
            return result
            
    except Exception as e:
        log_action(f"Error computing {algorithm.value} hash for {filepath}: {e}")
        return HashResult(algorithm, "", filepath, FileType.IMAGE, sha256_hash if 'sha256_hash' in locals() else "", 0.0, str(e))

def compute_video_hash(filepath: str, algorithm: HashAlgorithm = HashAlgorithm.DHASH, 
                      cache: Optional[HashCache] = None) -> HashResult:
    """Compute hash of a video file using frame extraction and perceptual hashing with optional caching."""
    # Check cache first
    if cache:
        cached_result = cache.get_cached_hash(filepath, algorithm)
        if cached_result:
            return cached_result
    
    # Always calculate SHA256 first
    sha256_hash = sha256_file(filepath)
    
    if not ffmpeg:
        # Fall back to file content hash if ffmpeg not available
        return HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, "ffmpeg-python not available")
    
    try:
        # Get video information first
        probe = ffmpeg.probe(filepath)
        
        # Find the video stream
        video_stream = None
        for stream in probe['streams']:
            if stream['codec_type'] == 'video':
                video_stream = stream
                break
        
        if not video_stream:
            return HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, "No video stream found")
        
        duration = float(video_stream.get('duration', 0))
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        
        if duration <= 0 or width <= 0 or height <= 0:
            return HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, "Invalid video dimensions or duration")
        
        # Extract multiple frames for better hash accuracy
        frame_times = [duration * 0.25, duration * 0.5, duration * 0.75]  # 25%, 50%, 75%
        frame_hashes = []
        
        for frame_time in frame_times:
            try:
                # Extract frame as PNG data
                frame_data = (
                    ffmpeg
                    .input(filepath, ss=frame_time)
                    .output('pipe:', vframes=1, format='png')
                    .run(capture_stdout=True, quiet=True)
                )
                
                if frame_data[0]:
                    # Convert frame data to PIL Image
                    from io import BytesIO
                    if Image:
                        frame_image = Image.open(BytesIO(frame_data[0]))
                        
                        # Compute perceptual hash of the frame
                        if algorithm == HashAlgorithm.DHASH and imagehash:
                            frame_hash = str(imagehash.dhash(frame_image))
                        elif algorithm == HashAlgorithm.PHASH and imagehash:
                            frame_hash = str(imagehash.phash(frame_image))
                        elif algorithm == HashAlgorithm.AHASH and imagehash:
                            frame_hash = str(imagehash.average_hash(frame_image))
                        elif algorithm == HashAlgorithm.WHASH and imagehash:
                            frame_hash = str(imagehash.whash(frame_image))
                        else:
                            # Fall back to basic hash of frame data
                            frame_hash = hashlib.sha256(frame_data[0]).hexdigest()[:16]
                        
                        frame_hashes.append(frame_hash)
                        
            except Exception as e:
                log_action(f"Error extracting frame at {frame_time}s from {filepath}: {e}")
                continue
        
        if frame_hashes:
            # Combine frame hashes into a single video hash
            combined_hash = hashlib.sha256('|'.join(frame_hashes).encode()).hexdigest()[:32]
            result = HashResult(algorithm, combined_hash, filepath, FileType.VIDEO, sha256_hash, 0.0)
            
            # Cache the result
            if cache:
                cache.cache_hash(result)
            
            return result
        else:
            # No frames could be extracted, fall back to file hash
            result = HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, "Could not extract any frames")
            
            # Cache even failed extraction results to avoid repeated attempts
            if cache:
                cache.cache_hash(result)
            
            return result
            
    except Exception as e:
        log_action(f"Error computing video hash for {filepath}: {e}")
        # Fall back to file content hash
        result = HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, str(e))
        
        # Cache error results to avoid repeated failed attempts
        if cache:
            cache.cache_hash(result)
        
        return result

def compute_video_similarity(video1_path: str, video2_path: str, algorithm: HashAlgorithm = HashAlgorithm.DHASH) -> float:
    """Compute similarity between two videos based on frame analysis."""
    hash1 = compute_video_hash(video1_path, algorithm)
    hash2 = compute_video_hash(video2_path, algorithm)
    
    if hash1.error or hash2.error or not hash1.hash_value or not hash2.hash_value:
        return 1.0  # Cannot compare, assume different
    
    return calculate_hash_similarity(hash1.hash_value, hash2.hash_value, algorithm)

def calculate_hash_similarity(hash1: str, hash2: str, algorithm: HashAlgorithm) -> float:
    """Calculate similarity between two hashes (0.0 = identical, 1.0 = completely different)."""
    if not hash1 or not hash2 or hash1 == hash2:
        return 0.0 if hash1 == hash2 else 1.0
    
    if algorithm == HashAlgorithm.SHA256:
        # SHA256 is exact match only
        return 0.0 if hash1 == hash2 else 1.0
    
    # For perceptual hashes, calculate Hamming distance
    if not imagehash:
        return 1.0
    
    try:
        hash_obj1 = imagehash.hex_to_hash(hash1)
        hash_obj2 = imagehash.hex_to_hash(hash2)
        hamming_distance = hash_obj1 - hash_obj2
        # Normalize to 0.0-1.0 range (64 is max distance for 8x8 hash)
        max_distance = len(hash1) * 4  # 4 bits per hex char
        return min(hamming_distance / max_distance, 1.0)
    except Exception as e:
        log_action(f"Error calculating hash similarity: {e}")
        return 1.0

def get_image_metadata(filepath: str) -> Dict[str, Any]:
    """Extract comprehensive metadata from image and video files."""
    meta = {}
    try:
        # Basic file system metadata
        meta = {
            "created": os.path.getctime(filepath),
            "modified": os.path.getmtime(filepath),
            "size": os.path.getsize(filepath),
            "name": os.path.basename(filepath),
            "path": filepath,
            "file_type": get_file_type(filepath).value,
        }
        
        file_type = get_file_type(filepath)
        
        if file_type == FileType.IMAGE:
            # Image-specific metadata
            try:
                if Image:
                    with Image.open(filepath) as img:
                        meta["width"] = img.width
                        meta["height"] = img.height
                        meta["mode"] = img.mode
                        meta["format"] = img.format
                        
                        # EXIF data using PIL
                        if hasattr(img, '_getexif') and img._getexif():
                            exif_dict = img._getexif()
                            meta["exif_data"] = exif_dict
                            
                            # Extract common EXIF fields
                            if 272 in exif_dict:  # Make
                                meta["camera_make"] = exif_dict[272]
                            if 271 in exif_dict:  # Model  
                                meta["camera_model"] = exif_dict[271]
                            if 306 in exif_dict:  # DateTime
                                meta["date_taken"] = exif_dict[306]
                            if 34853 in exif_dict:  # GPS Info
                                meta["gps_info"] = exif_dict[34853]
                
                # Enhanced EXIF using exifread library
                if exifread:
                    with open(filepath, 'rb') as f:
                        tags = exifread.process_file(f)
                        if tags:
                            meta["exif_tags"] = {str(key): str(tags[key]) for key in tags.keys()}
                            
            except Exception as e:
                log_action(f"Error reading image metadata for {filepath}: {e}")
        
        elif file_type == FileType.VIDEO:
            # Video-specific metadata
            try:
                if ffmpeg:
                    probe = ffmpeg.probe(filepath)
                    
                    # Find video and audio streams
                    video_stream = None
                    audio_stream = None
                    
                    for stream in probe.get('streams', []):
                        if stream['codec_type'] == 'video' and not video_stream:
                            video_stream = stream
                        elif stream['codec_type'] == 'audio' and not audio_stream:
                            audio_stream = stream
                    
                    # Extract video stream metadata
                    if video_stream:
                        meta["duration"] = float(video_stream.get('duration', 0))
                        meta["width"] = int(video_stream.get('width', 0))
                        meta["height"] = int(video_stream.get('height', 0))
                        meta["video_codec"] = video_stream.get('codec_name', '')
                        meta["video_bitrate"] = int(video_stream.get('bit_rate', 0))
                        meta["fps"] = video_stream.get('r_frame_rate', '')
                        meta["pixel_format"] = video_stream.get('pix_fmt', '')
                        
                        # Calculate resolution category
                        width = meta["width"]
                        height = meta["height"]
                        if width >= 3840 and height >= 2160:
                            meta["resolution_category"] = "4K"
                        elif width >= 1920 and height >= 1080:
                            meta["resolution_category"] = "1080p"
                        elif width >= 1280 and height >= 720:
                            meta["resolution_category"] = "720p"
                        elif width >= 854 and height >= 480:
                            meta["resolution_category"] = "480p"
                        else:
                            meta["resolution_category"] = "SD"
                    
                    # Extract audio stream metadata
                    if audio_stream:
                        meta["audio_codec"] = audio_stream.get('codec_name', '')
                        meta["audio_bitrate"] = int(audio_stream.get('bit_rate', 0))
                        meta["audio_channels"] = int(audio_stream.get('channels', 0))
                        meta["sample_rate"] = int(audio_stream.get('sample_rate', 0))
                    
                    # Extract container/format metadata
                    if 'format' in probe:
                        format_info = probe['format']
                        meta["container_format"] = format_info.get('format_name', '')
                        meta["total_bitrate"] = int(format_info.get('bit_rate', 0))
                        
                        # Extract common video tags
                        if 'tags' in format_info:
                            tags = format_info['tags']
                            meta["video_tags"] = tags
                            
                            # Map common tag names
                            tag_mapping = {
                                'title': 'video_title',
                                'artist': 'video_artist', 
                                'album': 'video_album',
                                'date': 'video_date',
                                'creation_time': 'video_creation_time',
                                'comment': 'video_comment',
                                'genre': 'video_genre',
                                'encoder': 'video_encoder'
                            }
                            
                            for tag_key, meta_key in tag_mapping.items():
                                if tag_key in tags:
                                    meta[meta_key] = tags[tag_key]
                                # Also check uppercase versions
                                elif tag_key.upper() in tags:
                                    meta[meta_key] = tags[tag_key.upper()]
                            
            except Exception as e:
                log_action(f"Error reading video metadata for {filepath}: {e}")
        
        # IPTC tags (images only)
        if file_type == FileType.IMAGE and iptcinfo3 is not None:
            try:
                info = iptcinfo3.IPTCInfo(filepath)
                if info:
                    meta["iptc_keywords"] = info.get('keywords', [])
                    meta["iptc_caption"] = info.get('caption/abstract', '')
                    meta["iptc_copyright"] = info.get('copyright notice', '')
            except Exception as e:
                log_action(f"Error reading IPTC for {filepath}: {e}")
        
        # XMP tags (images only)
        if file_type == FileType.IMAGE and libxmp is not None:
            try:
                xmpfile = XMPFiles(file_path=filepath)
                xmp = xmpfile.get_xmp()
                if xmp:
                    meta["xmp_keywords"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'subject')
                    meta["xmp_title"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'title')
                    meta["xmp_description"] = xmp.get_property(libxmp.consts.XMP_NS_DC, 'description')
                xmpfile.close_file()
            except Exception as e:
                log_action(f"Error reading XMP for {filepath}: {e}")
                
    except Exception as e:
        log_action(f"Error reading metadata for {filepath}: {e}")
    
    return meta

def get_file_type(filename: str) -> FileType:
    """Determine if a file is an image, video, or unknown type."""
    ext = Path(filename).suffix.lower().lstrip(".")
    
    image_extensions = {
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'heic', 'heif',
        'cr2', 'nef', 'arw', 'dng', 'raf', 'orf', 'rw2', 'pef', 'srw', 'x3f',
        'psd', 'xcf', 'svg', 'avif'
    }
    
    video_extensions = {
        'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v', '3gp', 'mts',
        'ts', 'vob', 'ogv', 'divx', 'xvid', 'rm', 'rmvb', 'asf'
    }
    
    if ext in image_extensions:
        return FileType.IMAGE
    elif ext in video_extensions:
        return FileType.VIDEO
    else:
        return FileType.UNKNOWN

def is_supported_file(filename: str, types: List[str]) -> bool:
    """Check if a file is supported based on user-specified types."""
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in [t.lower().lstrip(".") for t in types]

def is_image_file(filename: str, types: List[str]) -> bool:
    """Legacy function for backward compatibility."""
    return is_supported_file(filename, types) and get_file_type(filename) == FileType.IMAGE

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

def find_duplicates(dirs: List[str], types: List[str], exclude_dirs: List[str], 
                   similarity_threshold: float = 0.1, algorithm: HashAlgorithm = HashAlgorithm.DHASH,
                   max_workers: int = 4, chunk_size: int = None) -> Tuple[List[List[str]], Dict[str, 'HashResult']]:
    """Find duplicate files using optimized two-stage approach with memory-conscious processing."""
    
    # Check initial memory stats
    initial_memory = MemoryStats.current()
    log_action(f"Starting optimized duplicate detection. Memory usage: {initial_memory.percent_used:.1f}% ({initial_memory.used_mb:.0f}MB used)")
    
    # Count total files first for memory planning
    total_files = 0
    for d in dirs:
        if not os.path.exists(d):
            continue
        for root, _, filenames in os.walk(d):
            if any(ex in root for ex in exclude_dirs):
                continue
            total_files += sum(1 for fname in filenames if is_supported_file(fname, types))
    
    if total_files == 0:
        log_action("No supported files found in specified directories")
        return []
    
    log_action(f"Found {total_files} files to process - using two-stage optimization")
    
    # Determine processing strategy based on file count and memory
    if chunk_size is None:
        chunk_size = get_optimal_chunk_size(total_files, initial_memory.available_mb)
    
    # Stage 1: Fast SHA256 hashing for exact duplicates
    log_action("Stage 1: Computing SHA256 hashes for exact duplicate detection...")
    sha256_groups, unique_files = find_exact_duplicates_chunked(dirs, types, exclude_dirs, max_workers, chunk_size)
    
    # Stage 2: Perceptual hashing only for files with unique SHA256
    if algorithm != HashAlgorithm.SHA256 and unique_files:
        log_action(f"Stage 2: Computing {algorithm.value} hashes for {len(unique_files)} unique files...")
        similarity_groups, hash_results_dict = find_similarity_duplicates_optimized(
            unique_files, similarity_threshold, algorithm, max_workers, chunk_size
        )
        
        # Combine exact and similarity groups
        all_groups = sha256_groups + similarity_groups
        
        # Add SHA256 results to hash_results_dict
        for group in sha256_groups:
            for filepath in group:
                if filepath not in hash_results_dict:
                    hash_results_dict[filepath] = HashResult(
                        HashAlgorithm.SHA256, "", filepath, get_file_type(filepath), 
                        sha256_file(filepath), 0.0
                    )
    else:
        # SHA256 only or no unique files
        all_groups = sha256_groups
        hash_results_dict = {}
        for group in sha256_groups:
            for filepath in group:
                hash_results_dict[filepath] = HashResult(
                    HashAlgorithm.SHA256, "", filepath, get_file_type(filepath),
                    sha256_file(filepath), 0.0
                )
    
    # Final memory stats
    final_memory = MemoryStats.current()
    log_action(f"Optimized duplicate detection completed. Found {len(all_groups)} groups. "
              f"Memory usage: {final_memory.percent_used:.1f}% (peak reduction achieved)")
    
    return all_groups, hash_results_dict

def find_similarity_groups_efficient(hash_results: List[HashResult], threshold: float, 
                                   algorithm: HashAlgorithm) -> List[List[str]]:
    """Memory-efficient similarity grouping for large numbers of files."""
    if len(hash_results) < 2:
        return []
    
    log_action(f"Finding similarity groups for {len(hash_results)} files with threshold {threshold}")
    
    duplicate_groups = []
    processed = set()
    
    # For very large datasets, we might need to use a more sophisticated approach
    # For now, using the O(n²) approach but with memory management
    
    total_comparisons = (len(hash_results) * (len(hash_results) - 1)) // 2
    comparisons_done = 0
    
    for i, result1 in enumerate(hash_results):
        if result1.file_path in processed:
            continue
            
        similar_files = [result1.file_path]
        processed.add(result1.file_path)
        
        for j, result2 in enumerate(hash_results[i+1:], i+1):
            comparisons_done += 1
            
            if result2.file_path in processed:
                continue
                
            similarity = calculate_hash_similarity(result1.hash_value, result2.hash_value, algorithm)
            if similarity <= threshold:
                similar_files.append(result2.file_path)
                processed.add(result2.file_path)
                # Store similarity score in the result objects for later display
                result2.similarity_score = similarity
            
            # Log progress for very large datasets
            if comparisons_done % 10000 == 0:
                progress_pct = (comparisons_done / total_comparisons) * 100
                current_memory = MemoryStats.current()
                log_action(f"Similarity comparison progress: {progress_pct:.1f}% ({comparisons_done}/{total_comparisons}), Memory: {current_memory.percent_used:.1f}%")
        
        if len(similar_files) > 1:
            duplicate_groups.append(similar_files)
    
    return duplicate_groups

def find_exact_duplicates_chunked(dirs: List[str], types: List[str], exclude_dirs: List[str], 
                                 max_workers: int, chunk_size: int) -> Tuple[List[List[str]], List[str]]:
    """Stage 1: Fast SHA256-based exact duplicate detection with memory optimization."""
    sha256_map = {}
    processed_files = 0
    total_files = sum(1 for d in dirs if os.path.exists(d) 
                     for root, _, filenames in os.walk(d) 
                     if not any(ex in root for ex in exclude_dirs)
                     for fname in filenames if is_supported_file(fname, types))
    
    # Process in chunks to maintain memory efficiency
    for chunk_files in scan_files_chunked(dirs, types, exclude_dirs, chunk_size):
        chunk_hashes = {}
        
        # Compute SHA256 hashes in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(sha256_file, f): f for f in chunk_files}
            
            for future in concurrent.futures.as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    sha256_hash = future.result()
                    if sha256_hash:  # Valid hash
                        chunk_hashes[filepath] = sha256_hash
                except Exception as e:
                    log_action(f"Error computing SHA256 for {filepath}: {e}")
        
        # Group by hash within chunk
        for filepath, hash_value in chunk_hashes.items():
            sha256_map.setdefault(hash_value, []).append(filepath)
        
        processed_files += len(chunk_files)
        current_memory = MemoryStats.current()
        progress_pct = (processed_files / total_files) * 100
        log_action(f"SHA256 Progress: {processed_files}/{total_files} files ({progress_pct:.1f}%), Memory: {current_memory.percent_used:.1f}%")
        
        # Memory management
        if current_memory.percent_used > 85:
            log_action("High memory usage detected during SHA256 processing")
            gc.collect()
    
    # Separate exact duplicates from unique files
    duplicate_groups = [group for group in sha256_map.values() if len(group) > 1]
    unique_files = [group[0] for group in sha256_map.values() if len(group) == 1]
    
    total_exact_duplicates = sum(len(group) for group in duplicate_groups)
    log_action(f"Stage 1 complete: Found {len(duplicate_groups)} exact duplicate groups "
              f"({total_exact_duplicates} files). {len(unique_files)} files need similarity analysis.")
    
    return duplicate_groups, unique_files

def find_similarity_duplicates_optimized(unique_files: List[str], threshold: float, 
                                       algorithm: HashAlgorithm, max_workers: int, 
                                       chunk_size: int) -> Tuple[List[List[str]], Dict[str, 'HashResult']]:
    """Stage 2: LSH-optimized similarity detection with caching for files with unique SHA256."""
    # Initialize cache for performance boost
    cache = HashCache()
    cache.cleanup_old_entries(30)  # Clean up old entries
    
    # Process perceptual hashes in smaller chunks to manage memory
    similarity_chunk_size = min(chunk_size // 2, 1000)  # Smaller chunks for memory efficiency
    all_hash_results = []
    processed_files = 0
    cached_hits = 0
    
    # Process unique files in chunks
    for i in range(0, len(unique_files), similarity_chunk_size):
        chunk_files = unique_files[i:i + similarity_chunk_size]
        chunk_hash_results = []
        
        # Compute perceptual hashes for chunk with caching
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}
            for f in chunk_files:
                # Quick cache check before submitting expensive computation
                cached_result = cache.get_cached_hash(f, algorithm)
                if cached_result:
                    chunk_hash_results.append(cached_result)
                    cached_hits += 1
                else:
                    file_type = get_file_type(f)
                    if file_type == FileType.IMAGE:
                        future_to_file[executor.submit(compute_perceptual_hash, f, algorithm, cache)] = f
                    elif file_type == FileType.VIDEO:
                        future_to_file[executor.submit(compute_video_hash, f, algorithm, cache)] = f
            
            for future in concurrent.futures.as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    result = future.result()
                    if result.hash_value and not result.error:
                        chunk_hash_results.append(result)
                    elif result.error:
                        log_action(f"Perceptual hash failed for {filepath}: {result.error}")
                except Exception as e:
                    log_action(f"Error processing {filepath}: {e}")
        
        all_hash_results.extend(chunk_hash_results)
        processed_files += len(chunk_files)
        
        current_memory = MemoryStats.current()
        progress_pct = (processed_files / len(unique_files)) * 100
        cache_hit_pct = (cached_hits / processed_files) * 100 if processed_files > 0 else 0
        log_action(f"Similarity Progress: {processed_files}/{len(unique_files)} files ({progress_pct:.1f}%), "
                  f"Cache hits: {cache_hit_pct:.1f}%, Memory: {current_memory.percent_used:.1f}%")
        
        # Memory management between chunks
        if current_memory.percent_used > 80:
            log_action("High memory usage during similarity processing - forcing cleanup")
            gc.collect()
    
    # Use LSH-optimized similarity grouping
    if len(all_hash_results) > 1000:  # Use LSH for large datasets
        duplicate_groups = find_similarity_groups_lsh(all_hash_results, threshold, algorithm)
    else:
        duplicate_groups = find_similarity_groups_efficient(all_hash_results, threshold, algorithm)
    
    # Create hash results dictionary
    hash_results_dict = {result.file_path: result for result in all_hash_results}
    
    # Close cache connection
    cache.close()
    
    log_action(f"Stage 2 complete: Found {len(duplicate_groups)} similarity groups from {len(unique_files)} unique files. "
              f"Cache hit rate: {(cached_hits / len(unique_files)) * 100:.1f}%")
    
    return duplicate_groups, hash_results_dict

def find_similarity_groups_lsh(hash_results: List[HashResult], threshold: float, 
                              algorithm: HashAlgorithm) -> List[List[str]]:
    """LSH-based similarity grouping with progressive thresholds to reduce O(n²) comparisons."""
    from collections import defaultdict
    import struct
    
    if len(hash_results) < 2:
        return []
    
    log_action(f"Using LSH optimization with progressive thresholds for {len(hash_results)} files")
    
    # Progressive threshold strategy for memory efficiency
    coarse_threshold = min(threshold * 2.0, 0.3)  # Coarse filtering first
    fine_threshold = threshold  # Final precise threshold
    
    # LSH parameters tuned for the coarse threshold
    num_bands = 15  # Fewer bands for coarse filtering
    rows_per_band = 4  # More rows per band for better precision
    
    # Create LSH buckets for coarse filtering
    lsh_buckets = defaultdict(list)
    
    for result in hash_results:
        if not result.hash_value:
            continue
            
        try:
            # Convert hash to integers for LSH processing
            if len(result.hash_value) >= 16:  # Ensure sufficient hash length
                hash_bytes = bytes.fromhex(result.hash_value[:16])  # Use first 16 hex chars (8 bytes)
                hash_int = struct.unpack('>Q', hash_bytes)[0]  # Convert to 64-bit int
                
                # Generate LSH signatures using bit sampling
                for band in range(num_bands):
                    band_signature = []
                    for row in range(rows_per_band):
                        # Extract bits for this band/row combination
                        bit_pos = (band * rows_per_band + row) % 64
                        bit_value = (hash_int >> bit_pos) & 1
                        band_signature.append(bit_value)
                    
                    # Use tuple as bucket key
                    bucket_key = (band, tuple(band_signature))
                    lsh_buckets[bucket_key].append(result)
                    
        except (ValueError, struct.error) as e:
            log_action(f"LSH processing error for {result.file_path}: {e}")
            continue
    
    # Two-stage comparison: coarse then fine filtering
    duplicate_groups = []
    processed_files = set()
    
    bucket_comparisons = 0
    fine_comparisons = 0
    
    for bucket_files in lsh_buckets.values():
        if len(bucket_files) < 2:
            continue
            
        # Stage 1: Coarse comparison within bucket
        candidates = []
        for i, result1 in enumerate(bucket_files):
            if result1.file_path in processed_files:
                continue
                
            bucket_group = [result1]
            for result2 in bucket_files[i+1:]:
                bucket_comparisons += 1
                if result2.file_path in processed_files:
                    continue
                    
                # Quick coarse similarity check
                coarse_similarity = calculate_hash_similarity_fast(result1.hash_value, result2.hash_value, algorithm)
                if coarse_similarity <= coarse_threshold:
                    bucket_group.append(result2)
            
            if len(bucket_group) > 1:
                candidates.append(bucket_group)
        
        # Stage 2: Fine-grained comparison for candidates
        for candidate_group in candidates:
            final_group = [candidate_group[0]]
            processed_files.add(candidate_group[0].file_path)
            
            for result in candidate_group[1:]:
                if result.file_path in processed_files:
                    continue
                
                fine_comparisons += 1
                # Precise similarity calculation
                precise_similarity = calculate_hash_similarity(final_group[0].hash_value, result.hash_value, algorithm)
                if precise_similarity <= fine_threshold:
                    final_group.append(result)
                    processed_files.add(result.file_path)
                    result.similarity_score = precise_similarity
            
            if len(final_group) > 1:
                duplicate_groups.append([r.file_path for r in final_group])
    
    total_possible = len(hash_results) * (len(hash_results) - 1) // 2
    coarse_reduction = total_possible / max(bucket_comparisons, 1)
    fine_reduction = bucket_comparisons / max(fine_comparisons, 1)
    
    log_action(f"Progressive LSH: {bucket_comparisons} coarse + {fine_comparisons} fine comparisons vs {total_possible} naive")
    log_action(f"Reduction factors: Coarse {coarse_reduction:.1f}x, Fine {fine_reduction:.1f}x, Total {(total_possible / max(fine_comparisons, 1)):.1f}x")
    
    return duplicate_groups

def calculate_hash_similarity_fast(hash1: str, hash2: str, algorithm: HashAlgorithm) -> float:
    """Fast approximate similarity calculation for coarse filtering."""
    if not hash1 or not hash2 or hash1 == hash2:
        return 0.0 if hash1 == hash2 else 1.0
    
    if algorithm == HashAlgorithm.SHA256:
        return 0.0 if hash1 == hash2 else 1.0
    
    # Fast Hamming distance approximation using string comparison
    # This is less accurate but much faster for coarse filtering
    min_len = min(len(hash1), len(hash2))
    if min_len == 0:
        return 1.0
        
    differences = sum(c1 != c2 for c1, c2 in zip(hash1[:min_len], hash2[:min_len]))
    # Approximate normalization (4 bits per hex char)
    return min(differences / (min_len * 0.25), 1.0)  # Rough approximation

def rank_duplicates(dupe_group: List[str], path_preference: str = "shorter", filename_preference: str = None, 
                   quality_ranking: bool = False) -> List[str]:
    """Rank duplicates with enhanced criteria including optional quality analysis."""
    metas = []
    
    for f in dupe_group:
        meta = get_image_metadata(f)
        if meta:
            # Add quality metrics if enabled and file is an image
            if quality_ranking and get_file_type(f) == FileType.IMAGE:
                try:
                    quality_score = calculate_image_quality(f)
                    meta['quality_score'] = quality_score
                except Exception as e:
                    log_action(f"Error calculating quality for {f}: {e}")
                    meta['quality_score'] = 0.0
            else:
                meta['quality_score'] = 0.0
            metas.append(meta)
    
    if not metas:
        return dupe_group
    
    # Enhanced sorting with quality consideration
    def sort_key(m):
        quality = m.get('quality_score', 0.0)
        name_len = len(m.get("name", ""))
        path_len = len(m.get("path", ""))
        modified = m.get("modified", 0)
        size = m.get("size", 0)
        
        # Primary sort by quality (higher is better) if quality ranking enabled
        if quality_ranking:
            primary = -quality  # Negative for descending sort
        else:
            primary = 0
        
        # Secondary sorts
        if filename_preference == "longer":
            return (primary, -name_len, -path_len, -modified, -size)
        elif filename_preference == "shorter":
            return (primary, name_len, -path_len, -modified, -size)
        elif path_preference == "longer":
            return (primary, path_len, -modified, -size)
        else:  # shorter path (default)
            return (primary, -path_len, -modified, -size)
    
    metas.sort(key=sort_key)
    return [m["path"] for m in metas]

def calculate_image_quality(filepath: str) -> float:
    """Calculate image quality score using OpenCV (0.0 = poor, 1.0 = excellent)."""
    if not cv2:
        return 0.5  # Default score if OpenCV not available
    
    try:
        # Read image
        img = cv2.imread(filepath)
        if img is None:
            return 0.0
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate sharpness using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Normalize sharpness score (typical range 0-2000, normalize to 0-1)
        sharpness_score = min(laplacian_var / 2000.0, 1.0)
        
        # Calculate brightness score (avoid over/under exposure)
        mean_brightness = gray.mean()
        brightness_score = 1.0 - abs(mean_brightness - 128) / 128.0
        
        # Calculate contrast score
        contrast = gray.std()
        contrast_score = min(contrast / 64.0, 1.0)  # Normalize to 0-1
        
        # Weighted combination of quality metrics
        quality_score = (sharpness_score * 0.5 + brightness_score * 0.3 + contrast_score * 0.2)
        
        return min(max(quality_score, 0.0), 1.0)  # Clamp to 0-1 range
        
    except Exception as e:
        log_action(f"Error calculating image quality for {filepath}: {e}")
        return 0.5