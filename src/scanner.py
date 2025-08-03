import os
import hashlib
import concurrent.futures
import gc
import psutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Iterator, Generator
from enum import Enum
from dataclasses import dataclass
from src.config import log_action

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
    import libxmp
    from libxmp import XMPFiles, XMPMeta
except ImportError:
    libxmp = None

try:
    import exifread
except ImportError:
    exifread = None

BACKUP_DIR = "photochomper_backup"

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
        memory = psutil.virtual_memory()
        return cls(
            available_mb=memory.available / (1024 * 1024),
            used_mb=memory.used / (1024 * 1024),
            percent_used=memory.percent
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

def compute_perceptual_hash(filepath: str, algorithm: HashAlgorithm = HashAlgorithm.DHASH, hash_size: int = 8) -> HashResult:
    """Compute perceptual hash of an image file."""
    if not Image or not imagehash:
        return HashResult(algorithm, "", filepath, FileType.IMAGE, "", 0.0, "PIL/imagehash not available")
    
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
            
            return HashResult(algorithm, str(hash_obj), filepath, FileType.IMAGE, sha256_hash, 0.0)
            
    except Exception as e:
        log_action(f"Error computing {algorithm.value} hash for {filepath}: {e}")
        return HashResult(algorithm, "", filepath, FileType.IMAGE, sha256_hash if 'sha256_hash' in locals() else "", 0.0, str(e))

def compute_video_hash(filepath: str, algorithm: HashAlgorithm = HashAlgorithm.DHASH) -> HashResult:
    """Compute hash of a video file using frame extraction and perceptual hashing."""
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
            return HashResult(algorithm, combined_hash, filepath, FileType.VIDEO, sha256_hash, 0.0)
        else:
            # No frames could be extracted, fall back to file hash
            return HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, "Could not extract any frames")
            
    except Exception as e:
        log_action(f"Error computing video hash for {filepath}: {e}")
        # Fall back to file content hash
        return HashResult(algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, str(e))

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
                   max_workers: int = 4, chunk_size: int = None) -> List[List[str]]:
    """Find duplicate files using configurable hash algorithms with memory optimization."""
    
    # Check initial memory stats
    initial_memory = MemoryStats.current()
    log_action(f"Starting duplicate detection. Memory usage: {initial_memory.percent_used:.1f}% ({initial_memory.used_mb:.0f}MB used)")
    
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
    
    log_action(f"Found {total_files} files to process with {algorithm.value} algorithm")
    
    # Determine processing strategy based on file count and memory
    if chunk_size is None:
        chunk_size = get_optimal_chunk_size(total_files, initial_memory.available_mb)
    
    all_hash_results = []
    processed_files = 0
    
    # Process files in chunks to manage memory usage
    for chunk_files in scan_files_chunked(dirs, types, exclude_dirs, chunk_size):
        chunk_hash_results = []
        
        # Process current chunk with threading
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            if algorithm == HashAlgorithm.SHA256:
                # Use SHA256 for exact matching
                future_to_file = {executor.submit(sha256_file, f): f for f in chunk_files}
                for future in concurrent.futures.as_completed(future_to_file):
                    filepath = future_to_file[future]
                    try:
                        hash_value = future.result()
                        if hash_value:
                            chunk_hash_results.append(HashResult(algorithm, hash_value, filepath, get_file_type(filepath)))
                    except Exception as e:
                        log_action(f"Error processing {filepath}: {e}")
            else:
                # Use perceptual hashing for similarity matching
                future_to_file = {}
                for f in chunk_files:
                    file_type = get_file_type(f)
                    if file_type == FileType.IMAGE:
                        future_to_file[executor.submit(compute_perceptual_hash, f, algorithm)] = f
                    elif file_type == FileType.VIDEO:
                        future_to_file[executor.submit(compute_video_hash, f, algorithm)] = f
                
                for future in concurrent.futures.as_completed(future_to_file):
                    filepath = future_to_file[future]
                    try:
                        result = future.result()
                        if result.hash_value and not result.error:
                            chunk_hash_results.append(result)
                        elif result.error:
                            log_action(f"Hash computation failed for {filepath}: {result.error}")
                    except Exception as e:
                        log_action(f"Error processing {filepath}: {e}")
        
        # Add chunk results to overall results
        all_hash_results.extend(chunk_hash_results)
        processed_files += len(chunk_files)
        
        # Log progress and memory usage
        current_memory = MemoryStats.current()
        progress_pct = (processed_files / total_files) * 100
        log_action(f"Progress: {processed_files}/{total_files} files ({progress_pct:.1f}%), Memory: {current_memory.percent_used:.1f}%")
        
        # Warn if memory usage is getting high
        if current_memory.percent_used > 85:
            log_action(f"Warning: High memory usage ({current_memory.percent_used:.1f}%). Consider reducing chunk size.")
        
        # Force garbage collection between chunks
        gc.collect()
    
    log_action(f"Hash computation completed. Total hashes: {len(all_hash_results)}")
    
    # Group files by similarity using memory-efficient approach
    if algorithm == HashAlgorithm.SHA256:
        # Exact matching - can use simple hash map
        hash_map = {}
        for result in all_hash_results:
            hash_map.setdefault(result.hash_value, []).append(result.file_path)
        duplicate_groups = [group for group in hash_map.values() if len(group) > 1]
    else:
        # Similarity-based matching - use memory-efficient comparison
        duplicate_groups = find_similarity_groups_efficient(all_hash_results, similarity_threshold, algorithm)
    
    # Final memory stats
    final_memory = MemoryStats.current()
    log_action(f"Duplicate detection completed. Found {len(duplicate_groups)} groups. Final memory usage: {final_memory.percent_used:.1f}%")
    
    return duplicate_groups

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
            
            # Log progress for very large datasets
            if comparisons_done % 10000 == 0:
                progress_pct = (comparisons_done / total_comparisons) * 100
                current_memory = MemoryStats.current()
                log_action(f"Similarity comparison progress: {progress_pct:.1f}% ({comparisons_done}/{total_comparisons}), Memory: {current_memory.percent_used:.1f}%")
        
        if len(similar_files) > 1:
            duplicate_groups.append(similar_files)
    
    return duplicate_groups

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