import os
import hashlib
import concurrent.futures
import gc
import sqlite3
import json
import platform
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Iterator, Generator
from enum import Enum
from dataclasses import dataclass
from src.config import log_action

# Duplicate imports retained for compatibility across the module (harmless).
# They were added earlier to ensure imports are available in all code paths.
import os
import time
import platform
import struct
import hashlib
import concurrent.futures

# Optional dependencies - wrapped in try/except so the application remains usable
# even if optional libraries (psutil, PIL, imagehash, cv2, ffmpeg, etc.) are not installed.
try:
    import psutil
except ImportError:
    psutil = None

# Image processing imports - PIL and imagehash are preferred for perceptual hashing.
# If missing, functions that require them return sensible fallback results instead of crashing.
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
    # On Windows we prefer to skip libxmp due to Exempi build issues; log and continue.
    if platform.system() == "Windows":
        libxmp = None
        log_action(
            "Skipping XMP metadata extraction on Windows (Exempi library not available)"
        )
    else:
        import libxmp
        from libxmp import XMPFiles, XMPMeta
except ImportError:
    libxmp = None

try:
    import exifread
except ImportError:
    exifread = None

# Constants used by the module
BACKUP_DIR = "photochomper_backup"
HASH_CACHE_DB = "photochomper_hash_cache.db"


class HashAlgorithm(Enum):
    """Supported hash algorithms for duplicate detection.

    - SHA256: exact file content match
    - DHASH/PHASH/AHASH/WHASH: perceptual image hashes for similarity detection
    """

    SHA256 = "sha256"  # Exact content hash
    DHASH = "dhash"  # Difference hash (perceptual)
    PHASH = "phash"  # Perceptual hash
    AHASH = "ahash"  # Average hash
    WHASH = "whash"  # Wavelet hash


class FileType(Enum):
    """Categorize files processed by the scanner."""

    IMAGE = "image"
    VIDEO = "video"
    UNKNOWN = "unknown"


@dataclass
class HashResult:
    """Container for results returned from hash computations.

    Fields:
    - algorithm: which algorithm produced the hash
    - hash_value: perceptual or content hash (hex string)
    - file_path: original file path
    - file_type: FileType enum for downstream handling
    - sha256_hash: always computed for exact duplicate tracking
    - similarity_score: populated during pairwise comparisons (lower == more similar)
    - error: optional error message if computation failed
    """

    algorithm: HashAlgorithm
    hash_value: str
    file_path: str
    file_type: FileType
    sha256_hash: str = ""  # Always calculated SHA256 hash
    similarity_score: float = 0.0  # Similarity score for comparison
    error: Optional[str] = None


class HashCache:
    """SQLite-backed cache to avoid recalculating hashes for unchanged files.

    Design notes:
    - Uses a per-call sqlite3 connection (check_same_thread=False) for thread-friendly access.
    - Stores file size and mtime to quickly determine whether the on-disk file changed.
    - Returns HashResult objects for convenience.
    - Each public method is defensive: exceptions are logged and treated as cache miss.
    """

    def __init__(self, cache_file: str = HASH_CACHE_DB):
        self.cache_file = cache_file
        self._init_db()

    def _get_connection(self):
        """Return a new sqlite3 connection suitable for multi-threaded use.

        Using new connections per thread avoids shared-connection locks and cross-thread issues.
        """
        try:
            conn = sqlite3.connect(self.cache_file, check_same_thread=False)
            return conn
        except Exception as e:
            log_action(f"Error getting database connection: {e}")
            return None

    def _init_db(self):
        """Create cache table and indexes on first use.

        The schema stores both perceptual and sha256 hashes, along with file stats and timestamp.
        """
        try:
            conn = self._get_connection()
            if conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hash_cache (
                        filepath TEXT PRIMARY KEY,
                        file_size INTEGER,
                        file_mtime REAL,
                        algorithm TEXT,
                        sha256_hash TEXT,
                        perceptual_hash TEXT,
                        cached_at REAL
                    )
                """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_filepath ON hash_cache(filepath)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_algorithm ON hash_cache(algorithm)"
                )
                conn.commit()
                conn.close()
                log_action(f"Hash cache initialized: {self.cache_file}")
        except Exception as e:
            # Initialization failures are non-fatal; scanner will proceed without cache.
            log_action(f"Error initializing hash cache: {e}")

    def get_cached_hash(
        self, filepath: str, algorithm: HashAlgorithm
    ) -> Optional[HashResult]:
        """
        Return a HashResult if cache contains a valid, up-to-date entry for filepath+algorithm.

        Validation:
        - Ensures cached file_size and file_mtime match current file stats (mtime tolerance 1s).
        - Defensive type checks are performed because SQLite can return unexpected types.
        - Returns None for any error or mismatch so caller will recompute the hash.
        """
        conn = self._get_connection()
        if not conn:
            return None

        try:
            stat = os.stat(filepath)
            file_size = stat.st_size
            file_mtime = stat.st_mtime

            cursor = conn.execute(
                """
                SELECT sha256_hash, perceptual_hash, file_size, file_mtime 
                FROM hash_cache 
                WHERE filepath = ? AND algorithm = ?
            """,
                (filepath, algorithm.value),
            )

            row = cursor.fetchone()
            if row:
                try:
                    cached_sha256, cached_perceptual, cached_size, cached_mtime = row

                    # --- FIX: Convert to correct types if needed ---
                    if isinstance(cached_size, str):
                        try:
                            cached_size = int(cached_size)
                        except Exception:
                            log_action(
                                f"Invalid cached size for {filepath}: {cached_size}"
                            )
                            return None
                    if isinstance(cached_mtime, str):
                        try:
                            cached_mtime = float(cached_mtime)
                        except Exception:
                            log_action(
                                f"Invalid cached mtime for {filepath}: {cached_mtime}"
                            )
                            return None

                    if not isinstance(cached_size, (int, float)) or not isinstance(
                        cached_mtime, (int, float)
                    ):
                        log_action(
                            f"Invalid cached data types for {filepath}: size={type(cached_size)}, mtime={type(cached_mtime)}"
                        )
                        return None

                    if not isinstance(file_size, (int, float)) or not isinstance(
                        file_mtime, (int, float)
                    ):
                        log_action(
                            f"Invalid file stat types for {filepath}: size={type(file_size)}, mtime={type(file_mtime)}"
                        )
                        return None

                    if (
                        cached_size == file_size
                        and abs(cached_mtime - file_mtime) < 1.0
                    ):
                        return HashResult(
                            algorithm=algorithm,
                            hash_value=cached_perceptual or "",
                            file_path=filepath,
                            file_type=get_file_type(filepath),
                            sha256_hash=cached_sha256 or "",
                            similarity_score=0.0,
                        )
                except Exception as inner_e:
                    log_action(
                        f"Error processing cached data for {filepath}: {inner_e}"
                    )
                    return None
        except Exception as e:
            log_action(f"Error retrieving cached hash for {filepath}: {e}")
        finally:
            if conn:
                conn.close()
        return None

    def cache_hash(self, result: HashResult):
        """
        Insert or update the cache with HashResult for the given file.

        Always stores current file size and mtime so subsequent runs can validate cache entries.
        """
        if not result.file_path:
            return

        conn = self._get_connection()
        if not conn:
            return

        try:
            # --- FIX: Only cache if file exists ---
            if not os.path.exists(result.file_path):
                log_action(f"File does not exist, not caching: {result.file_path}")
                return

            stat = os.stat(result.file_path)
            import time

            conn.execute(
                """
                INSERT OR REPLACE INTO hash_cache 
                (filepath, file_size, file_mtime, algorithm, sha256_hash, perceptual_hash, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.file_path,
                    int(stat.st_size),
                    float(stat.st_mtime),
                    result.algorithm.value,
                    result.sha256_hash,
                    result.hash_value,
                    time.time(),
                ),
            )
            conn.commit()
        except Exception as e:
            log_action(f"Error caching hash for {result.file_path}: {e}")
        finally:
            if conn:
                conn.close()

    def cleanup_old_entries(self, days_old: int = 30):
        """Prune cache rows older than days_old to prevent unbounded DB growth."""
        conn = self._get_connection()
        if not conn:
            return

        try:
            import time

            cutoff_time = time.time() - (days_old * 24 * 3600)

            cursor = conn.execute(
                "DELETE FROM hash_cache WHERE cached_at < ?", (cutoff_time,)
            )
            deleted = cursor.rowcount
            conn.commit()

            if deleted > 0:
                log_action(f"Cleaned up {deleted} old cache entries")
        except Exception as e:
            log_action(f"Error cleaning up cache: {e}")
        finally:
            if conn:
                conn.close()

    def close(self):
        """No-op close: connections are created and closed per-call to avoid long-lived shared state."""
        pass


@dataclass
class SimilarityMatch:
    """Simple container for storing a discovered similar pair."""

    file1: str
    file2: str
    algorithm: HashAlgorithm
    similarity_score: float
    hash1: str
    hash2: str


@dataclass
class ProgressStats:
    """Structure used to report progress back to caller/UI.

    The application can create ProgressStats and pass to a progress_callback for UI updates.
    """

    phase: str
    current_step: int
    total_steps: int
    files_processed: int
    total_files: int
    start_time: float
    phase_start_time: float
    estimated_completion_time: float = 0.0

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def phase_elapsed_time(self) -> float:
        return time.time() - self.phase_start_time

    @property
    def progress_percent(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100

    @property
    def files_percent(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.files_processed / self.total_files) * 100


@dataclass
class MemoryStats:
    """Lightweight wrapper for reporting memory usage.

    Uses psutil when available for accurate reporting; otherwise falls back to conservative estimates.
    """

    available_mb: float
    used_mb: float
    percent_used: float

    @classmethod
    def current(cls) -> "MemoryStats":
        """Return current memory usage.

        psutil is preferred; on Unix the resource module is used as a fallback. When all else fails,
        reasonable defaults are returned so the memory-aware heuristics can still run.
        """
        if psutil:
            memory = psutil.virtual_memory()
            return cls(
                available_mb=memory.available / (1024 * 1024),
                used_mb=memory.used / (1024 * 1024),
                percent_used=memory.percent,
            )
        else:
            # Fallback when psutil is not available (best-effort)
            import resource

            try:
                # ru_maxrss is platform dependent; convert KB -> MB where applicable.
                usage = resource.getrusage(resource.RUSAGE_SELF)
                used_mb = usage.ru_maxrss / 1024  # Convert KB to MB
                return cls(
                    available_mb=2048.0,  # Conservative assumed availability
                    used_mb=used_mb,
                    percent_used=min(used_mb / 2048.0 * 100, 100.0),
                )
            except Exception:
                # Ultimate fallback: safe defaults (prevent divide by zero in heuristics)
                return cls(
                    available_mb=2048.0,
                    used_mb=512.0,  # Conservative estimate
                    percent_used=25.0,
                )


def get_optimal_chunk_size(
    total_files: int, available_memory_mb: float = None, user_chunk_size: int = None
) -> int:
    """Decide chunk size (files per batch) based on available memory and collection size.

    The function attempts to balance performance and memory usage:
    - Honor a non-negative user_chunk_size if provided.
    - Estimate memory per file and scale chunk size with total available memory.
    - Ensure a minimum chunk size to avoid too many small batches.
    """
    if user_chunk_size is not None:
        if user_chunk_size <= 0:
            # User explicitly disables chunking; process all files at once.
            log_action(
                f"Chunking disabled by user - processing all {total_files} files at once"
            )
            return total_files
        else:
            # Use user-specified chunk size but clamp to total_files.
            log_action(
                f"Using user-specified chunk size: {user_chunk_size} files per chunk"
            )
            return min(user_chunk_size, total_files)

    if available_memory_mb is None:
        memory_stats = MemoryStats.current()
        available_memory_mb = memory_stats.available_mb

    # Heuristics tuned for typical desktop/server RAM sizes.
    if available_memory_mb > 8000:  # >8GB RAM
        memory_factor = 0.35  # Use more memory
        max_chunk_size = 2000
    elif available_memory_mb > 4000:  # >4GB RAM
        memory_factor = 0.30
        max_chunk_size = 1500
    elif available_memory_mb > 2000:  # >2GB RAM
        memory_factor = 0.25
        max_chunk_size = 1000
    else:  # Low memory system
        memory_factor = 0.20
        max_chunk_size = 500

    usable_memory_mb = available_memory_mb * memory_factor

    # Estimate memory per file; tuned conservatively for hash + metadata overhead.
    if total_files > 50000:
        estimated_memory_per_file_kb = 12
    elif total_files > 10000:
        estimated_memory_per_file_kb = 10
    else:
        estimated_memory_per_file_kb = 8

    max_files_in_memory = int((usable_memory_mb * 1024) / estimated_memory_per_file_kb)

    # Determine sensible chunk size given constraints and provide helpful logging.
    if total_files <= max_files_in_memory and total_files <= max_chunk_size:
        chunk_size = total_files
        log_action(
            f"Memory optimization: All {total_files} files fit in memory - no chunking needed"
        )
    else:
        # Ensure chunk size not too small and bounded by max_chunk_size
        chunk_size = max(min(max_files_in_memory, max_chunk_size, total_files), 100)
        estimated_chunks = (total_files + chunk_size - 1) // chunk_size
        log_action(
            f"Memory optimization: Processing {total_files} files in {estimated_chunks} chunks of {chunk_size}"
        )
        log_action(
            f"Memory analysis: {available_memory_mb:.0f}MB available, using {usable_memory_mb:.0f}MB ({memory_factor*100:.0f}%)"
        )

    return chunk_size


def get_chunk_size_recommendations(
    total_files: int, available_memory_mb: float = None
) -> dict:
    """Produce a set of recommended chunk sizes for different trade-offs.

    Useful for UI/tooling to show users what's possible (conservative/balanced/performance).
    """
    if available_memory_mb is None:
        memory_stats = MemoryStats.current()
        available_memory_mb = memory_stats.available_mb

    recommendations = {}

    scenarios = [
        ("conservative", 0.15, "Lowest memory usage, slower processing"),
        ("balanced", 0.25, "Good balance of speed and memory usage (recommended)"),
        ("performance", 0.35, "Faster processing, higher memory usage"),
    ]

    for name, memory_factor, description in scenarios:
        usable_memory_mb = available_memory_mb * memory_factor
        estimated_memory_per_file_kb = 10
        max_files_in_memory = int(
            (usable_memory_mb * 1024) / estimated_memory_per_file_kb
        )

        if total_files <= max_files_in_memory:
            chunk_size = total_files
            estimated_chunks = 1
        else:
            chunk_size = max(min(max_files_in_memory, 2000), 100)
            estimated_chunks = (total_files + chunk_size - 1) // chunk_size

        recommendations[name] = {
            "chunk_size": chunk_size,
            "estimated_chunks": estimated_chunks,
            "memory_usage_mb": usable_memory_mb,
            "description": description,
        }

    return recommendations


def scan_files_chunked(
    dirs: List[str], types: List[str], exclude_dirs: List[str], chunk_size: int = None
) -> Generator[List[str], None, None]:
    """Walk provided directories and yield lists of supported files in chunks.

    This is the single place that enumerates filesystem entries; downstream stages
    can consume these chunks to keep working-set memory small.
    """
    all_files = []

    # First collect all matching files (filtering excluded directories)
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

    # Determine chunk size if caller didn't provide one
    if chunk_size is None:
        chunk_size = get_optimal_chunk_size(len(all_files))

    log_action(f"Scanning {len(all_files)} files in chunks of {chunk_size}")

    # Yield slices of the full list; caller will manage GC between batches
    for i in range(0, len(all_files), chunk_size):
        chunk = all_files[i : i + chunk_size]
        yield chunk

        # Free memory between chunks to keep resident set small
        if i + chunk_size < len(all_files):  # Not the last chunk
            gc.collect()


def sha256_file(filepath: str) -> str:
    """Compute SHA-256 digest of a file in streaming fashion.

    Returns hex digest string or empty string on error.
    """
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log_action(f"Error hashing file {filepath}: {e}")
        return ""


def compute_perceptual_hash(
    filepath: str,
    algorithm: HashAlgorithm = HashAlgorithm.DHASH,
    *,
    hash_size: int = 8,
    cache: Optional[HashCache] = None,
) -> HashResult:
    """
    Compute a perceptual hash for an image with optional caching.

    Note: 'cache' is keyword-only to prevent accidental positional misuse.
    """
    if not Image or not imagehash:
        return HashResult(
            algorithm,
            "",
            filepath,
            FileType.IMAGE,
            "",
            0.0,
            "PIL/imagehash not available",
        )

    # Always use cache as keyword argument
    if cache:
        try:
            cached_result = cache.get_cached_hash(filepath, algorithm)
        except Exception as e:
            log_action(f"Cache lookup error for {filepath}: {e}")
            cached_result = None
        if cached_result:
            return cached_result

    try:
        sha256_hash = sha256_file(filepath)
        with Image.open(filepath) as img:
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")
            if algorithm == HashAlgorithm.DHASH:
                h = imagehash.dhash(img, hash_size)
            elif algorithm == HashAlgorithm.PHASH:
                h = imagehash.phash(img, hash_size)
            elif algorithm == HashAlgorithm.AHASH:
                h = imagehash.average_hash(img, hash_size)
            elif algorithm == HashAlgorithm.WHASH:
                h = imagehash.whash(img, hash_size)
            else:
                h = imagehash.dhash(img, hash_size)
            hexhash = h.__str__()
            result = HashResult(
                algorithm, hexhash, filepath, FileType.IMAGE, sha256_hash, 0.0, None
            )
            if cache:
                try:
                    cache.cache_hash(result)
                except Exception as e:
                    log_action(f"Cache store error for {filepath}: {e}")
            return result
    except Exception as e:
        log_action(f"Error computing {algorithm.value} hash for {filepath}: {e}")
        return HashResult(
            algorithm,
            "",
            filepath,
            FileType.IMAGE,
            sha256_hash if "sha256_hash" in locals() else "",
            0.0,
            str(e),
        )


def compute_video_hash(
    filepath: str,
    algorithm: HashAlgorithm = HashAlgorithm.DHASH,
    cache: Optional[HashCache] = None,
) -> HashResult:
    """Compute a representative hash for a video by extracting and hashing multiple frames.

    Strategy:
    - Probe video metadata (duration, resolution) with ffmpeg.
    - Extract several frames at fractional positions (25/50/75%) to capture visual content.
    - Hash each frame perceptually and combine into a single deterministic hash.
    - If ffmpeg or PIL is missing, fall back to SHA256-derived hash.
    - Cache results where possible.
    """
    # Try cache first to avoid expensive ffmpeg work
    if cache:
        cached_result = cache.get_cached_hash(filepath, algorithm)
        if cached_result:
            return cached_result

    # Keep file content hash for exact dedupe fallback
    sha256_hash = sha256_file(filepath)

    if not ffmpeg:
        # If ffmpeg not available, fall back to content-based hash with an explanatory error.
        return HashResult(
            algorithm,
            sha256_hash,
            filepath,
            FileType.VIDEO,
            sha256_hash,
            0.0,
            "ffmpeg-python not available",
        )

    try:
        if not os.path.exists(filepath) or not os.access(filepath, os.R_OK):
            return HashResult(
                algorithm,
                sha256_hash,
                filepath,
                FileType.VIDEO,
                sha256_hash,
                0.0,
                "File not found or not readable",
            )

        # Use ffmpeg.probe to retrieve stream info (fast compared to full decode)
        probe = ffmpeg.probe(filepath)

        # Find video stream for duration/resolution metadata
        video_stream = None
        for stream in probe["streams"]:
            if stream["codec_type"] == "video":
                video_stream = stream
                break

        if not video_stream:
            return HashResult(
                algorithm,
                sha256_hash,
                filepath,
                FileType.VIDEO,
                sha256_hash,
                0.0,
                "No video stream found",
            )

        duration = float(video_stream.get("duration", 0))
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))

        if duration <= 0 or width <= 0 or height <= 0:
            return HashResult(
                algorithm,
                sha256_hash,
                filepath,
                FileType.VIDEO,
                sha256_hash,
                0.0,
                "Invalid video dimensions or duration",
            )

        # Choose several frame times for robustness (middle-heavy sampling)
        frame_times = [duration * 0.25, duration * 0.5, duration * 0.75]
        frame_hashes = []

        for frame_time in frame_times:
            try:
                # Extract a single frame as PNG bytes via ffmpeg pipe
                frame_data = (
                    ffmpeg.input(filepath, ss=frame_time)
                    .output("pipe:", vframes=1, format="png")
                    .run(capture_stdout=True, quiet=True)
                )

                if frame_data[0]:
                    from io import BytesIO

                    if Image:
                        frame_image = Image.open(BytesIO(frame_data[0]))

                        # Compute perceptual hash for the extracted frame
                        if algorithm == HashAlgorithm.DHASH and imagehash:
                            frame_hash = str(imagehash.dhash(frame_image))
                        elif algorithm == HashAlgorithm.PHASH and imagehash:
                            frame_hash = str(imagehash.phash(frame_image))
                        elif algorithm == HashAlgorithm.AHASH and imagehash:
                            frame_hash = str(imagehash.average_hash(frame_image))
                        elif algorithm == HashAlgorithm.WHASH and imagehash:
                            frame_hash = str(imagehash.whash(frame_image))
                        else:
                            # If imagehash not available, fallback to truncated SHA256 of frame bytes.
                            frame_hash = hashlib.sha256(frame_data[0]).hexdigest()[:16]

                        frame_hashes.append(frame_hash)

            except Exception as e:
                # Log and continue to next frame instead of failing the whole operation.
                log_action(
                    f"Error extracting frame at {frame_time}s from {filepath}: {e}"
                )
                continue

        if frame_hashes:
            # Deterministically combine per-frame hashes into one representative value.
            combined_hash = hashlib.sha256("|".join(frame_hashes).encode()).hexdigest()[
                :32
            ]
            result = HashResult(
                algorithm, combined_hash, filepath, FileType.VIDEO, sha256_hash, 0.0
            )

            # Cache the result for future runs
            if cache:
                cache.cache_hash(result)

            return result
        else:
            # No frames extracted - use file hash as fallback and cache that outcome.
            result = HashResult(
                algorithm,
                sha256_hash,
                filepath,
                FileType.VIDEO,
                sha256_hash,
                0.0,
                "Could not extract any frames",
            )
            if cache:
                cache.cache_hash(result)
            return result

    except Exception as e:
        # On any unexpected error, return a safe fallback and cache to avoid repeated work.
        log_action(f"Error computing video hash for {filepath}: {e}")
        result = HashResult(
            algorithm, sha256_hash, filepath, FileType.VIDEO, sha256_hash, 0.0, str(e)
        )
        if cache:
            cache.cache_hash(result)
        return result


def compute_video_similarity(
    video1_path: str, video2_path: str, algorithm: HashAlgorithm = HashAlgorithm.DHASH
) -> float:
    """Top-level convenience wrapper to compare two videos.

    Returns a normalized similarity score (0.0 identical, 1.0 completely different).
    """
    hash1 = compute_video_hash(video1_path, algorithm)
    hash2 = compute_video_hash(video2_path, algorithm)

    # If either video failed to produce a usable perceptual hash, treat as different.
    if hash1.error or hash2.error or not hash1.hash_value or not hash2.hash_value:
        return 1.0  # Cannot compare reliably

    return calculate_hash_similarity(hash1.hash_value, hash2.hash_value, algorithm)


def calculate_hash_similarity(
    hash1: str, hash2: str, algorithm: HashAlgorithm
) -> float:
    """Compute normalized similarity between two hex hash strings.

    For perceptual hashes we compute Hamming distance using imagehash hex_to_hash
    and normalize by maximum possible distance for the hash length.
    """
    if not hash1 or not hash2 or hash1 == hash2:
        return 0.0 if hash1 == hash2 else 1.0

    if algorithm == HashAlgorithm.SHA256:
        # Exact match only for SHA256
        return 0.0 if hash1 == hash2 else 1.0

    if not imagehash:
        # imagehash missing -> cannot compute perceptual similarity
        return 1.0

    try:
        hash_obj1 = imagehash.hex_to_hash(hash1)
        hash_obj2 = imagehash.hex_to_hash(hash2)
        # imagehash Hash objects implement '-' to compute Hamming distance
        hamming_distance = hash_obj1 - hash_obj2
        # Normalize to 0.0-1.0. Each hex char = 4 bits.
        max_distance = len(hash1) * 4
        return min(hamming_distance / max_distance, 1.0)
    except Exception as e:
        log_action(f"Error calculating hash similarity: {e}")
        return 1.0


def get_image_metadata(filepath: str) -> Dict[str, Any]:
    """
    Extract file metadata for ranking/quality heuristics.
    """
    meta = {}
    try:
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
            try:
                if Image:
                    with Image.open(filepath) as img:
                        meta["width"] = img.width
                        meta["height"] = img.height
                        meta["mode"] = img.mode
                        meta["format"] = img.format
                        if hasattr(img, "_getexif") and img._getexif():
                            exif_dict = img._getexif()
                            meta["exif_data"] = exif_dict
                            if 272 in exif_dict:
                                meta["camera_make"] = exif_dict[272]
                            if 271 in exif_dict:
                                meta["camera_model"] = exif_dict[271]
                            if 306 in exif_dict:
                                meta["date_taken"] = exif_dict[306]
                            if 34853 in exif_dict:
                                meta["gps_info"] = exif_dict[34853]
                if exifread:
                    with open(filepath, "rb") as f:
                        tags = exifread.process_file(f)
                        if tags:
                            meta["exif_tags"] = {
                                str(key): str(tags[key]) for key in tags.keys()
                            }
            except Exception as e:
                log_action(f"Error reading image metadata for {filepath}: {e}")

        elif file_type == FileType.VIDEO:
            try:
                if ffmpeg:
                    probe = ffmpeg.probe(filepath)
                    video_stream = None
                    audio_stream = None
                    for stream in probe.get("streams", []):
                        if stream["codec_type"] == "video" and not video_stream:
                            video_stream = stream
                        elif stream["codec_type"] == "audio" and not audio_stream:
                            audio_stream = stream
                    if video_stream:
                        meta["duration"] = float(video_stream.get("duration", 0))
                        meta["width"] = int(video_stream.get("width", 0))
                        meta["height"] = int(video_stream.get("height", 0))
                        meta["video_codec"] = video_stream.get("codec_name", "")
                        meta["video_bitrate"] = int(video_stream.get("bit_rate", 0))
                        meta["fps"] = video_stream.get("r_frame_rate", "")
                        meta["pixel_format"] = video_stream.get("pix_fmt", "")
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
                    if audio_stream:
                        meta["audio_codec"] = audio_stream.get("codec_name", "")
                        meta["audio_bitrate"] = int(audio_stream.get("bit_rate", 0))
                        meta["audio_channels"] = int(audio_stream.get("channels", 0))
                        meta["sample_rate"] = int(audio_stream.get("sample_rate", 0))
                    if "format" in probe:
                        format_info = probe["format"]
                        meta["container_format"] = format_info.get("format_name", "")
                        meta["total_bitrate"] = int(format_info.get("bit_rate", 0))
                        if "tags" in format_info:
                            tags = format_info["tags"]
                            meta["video_tags"] = tags
                            tag_mapping = {
                                "title": "video_title",
                                "artist": "video_artist",
                                "album": "video_album",
                                "date": "video_date",
                                "creation_time": "video_creation_time",
                                "comment": "video_comment",
                                "genre": "video_genre",
                                "encoder": "video_encoder",
                            }
                            for tag_key, meta_key in tag_mapping.items():
                                if tag_key in tags:
                                    meta[meta_key] = tags[tag_key]
                                elif tag_key.upper() in tags:
                                    meta[meta_key] = tags[tag_key.upper()]
            except Exception as e:
                log_action(f"Error reading video metadata for {filepath}: {e}")

        # --- FIX: IPTCInfo3 .get() -> dict access ---
        if file_type == FileType.IMAGE and iptcinfo3 is not None:
            try:
                with suppress_stdout_stderr():
                    info = iptcinfo3.IPTCInfo(filepath)
                if info:
                    meta["iptc_keywords"] = info["keywords"] if "keywords" in info else []
                    meta["iptc_caption"] = info["caption/abstract"] if "caption/abstract" in info else ""
                    meta["iptc_copyright"] = info["copyright notice"] if "copyright notice" in info else ""
            except Exception as e:
                log_action(f"Error reading IPTC for {filepath}: {e}")

        if file_type == FileType.IMAGE and libxmp is not None:
            try:
                xmpfile = XMPFiles(file_path=filepath)
                xmp = xmpfile.get_xmp()
                if xmp:
                    meta["xmp_keywords"] = xmp.get_property(
                        libxmp.consts.XMP_NS_DC, "subject"
                    )
                    meta["xmp_title"] = xmp.get_property(
                        libxmp.consts.XMP_NS_DC, "title"
                    )
                    meta["xmp_description"] = xmp.get_property(
                        libxmp.consts.XMP_NS_DC, "description"
                    )
                xmpfile.close_file()
            except Exception as e:
                log_action(f"Error reading XMP for {filepath}: {e}")

    except Exception as e:
        log_action(f"Error reading metadata for {filepath}: {e}")

    return meta


def get_file_type(filename: str) -> FileType:
    """Return FileType derived from file extension.

    The extension lists are intentionally broad to cover common RAW and less-common formats.
    """
    ext = Path(filename).suffix.lower().lstrip(".")

    image_extensions = {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "tif",
        "webp",
        "heic",
        "heif",
        "cr2",
        "nef",
        "arw",
        "dng",
        "raf",
        "orf",
        "rw2",
        "pef",
        "srw",
        "x3f",
        "psd",
        "xcf",
        "svg",
        "avif",
    }

    video_extensions = {
        "mp4",
        "avi",
        "mov",
        "mkv",
        "wmv",
        "flv",
        "webm",
        "m4v",
        "3gp",
        "mts",
        "ts",
        "vob",
        "ogv",
        "divx",
        "xvid",
        "rm",
        "rmvb",
        "asf",
    }

    if ext in image_extensions:
        return FileType.IMAGE
    elif ext in video_extensions:
        return FileType.VIDEO
    else:
        return FileType.UNKNOWN


def is_supported_file(filename: str, types: List[str]) -> bool:
    """Return True if filename's extension is in the provided types list.

    Caller should pass a list like ['jpg','png','mp4'] or similar. This keeps filtering centralized.
    """
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in [t.lower().lstrip(".") for t in types]


def is_image_file(filename: str, types: List[str]) -> bool:
    """Backward-compatible wrapper to check if a file is an image (based on types and extension)."""
    return (
        is_supported_file(filename, types) and get_file_type(filename) == FileType.IMAGE
    )


def backup_file(filepath: str):
    """Simple file backup helper used before destructive operations.

    Creates backup directory and copies the file if the backup doesn't already exist.
    """
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        dest = os.path.join(BACKUP_DIR, os.path.basename(filepath))
        if not os.path.exists(dest):
            with open(filepath, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
        log_action(f"Backed up {filepath} to {dest}")
    except Exception as e:
        log_action(f"Error backing up {filepath}: {e}")


def find_duplicates(
    dirs: List[str],
    types: List[str],
    exclude_dirs: List[str],
    similarity_threshold: float = 0.1,
    algorithm: HashAlgorithm = HashAlgorithm.DHASH,
    max_workers: int = 4,
    chunk_size: int = None,
    skip_sha256: bool = False,
    progress_callback: Optional[callable] = None,
) -> Tuple[List[List[str]], Dict[str, "HashResult"]]:
    """Main entrypoint for duplicate scanning.

    Two-stage strategy:
    1) SHA256 exact dedupe (fast, parallelizable)
    2) Perceptual hashing and similarity grouping for files with unique SHA256
    """

    start_time = time.time()

    # Log initial memory usage for telemetry and decision making
    initial_memory = MemoryStats.current()
    log_action(
        f"Starting optimized duplicate detection. Memory usage: {initial_memory.percent_used:.1f}% ({initial_memory.used_mb:.0f}MB used)"
    )

    # Optional initial progress callback to allow UI to show discovery start
    if progress_callback:
        progress_callback(
            ProgressStats("File Discovery", 0, 1, 0, 0, start_time, time.time())
        )

    # Count total files so progress and chunking heuristics can be accurate
    total_files = 0
    for d in dirs:
        if not os.path.exists(d):
            continue
        for root, _, filenames in os.walk(d):
            if any(ex in root for ex in exclude_dirs):
                continue
            total_files += sum(
                1 for fname in filenames if is_supported_file(fname, types)
            )

    if total_files == 0:
        log_action("No supported files found in specified directories")
        return [], {}

    log_action(f"Found {total_files} files to process - using two-stage optimization")

    # Choose chunk size based on memory or user preference
    if chunk_size is None:
        chunk_size = get_optimal_chunk_size(total_files, initial_memory.available_mb)
    else:
        chunk_size = get_optimal_chunk_size(
            total_files, initial_memory.available_mb, chunk_size
        )

    # If SHA256 is disabled or algorithm is SHA256, adjust stage count appropriately
    total_stages = 2 if not skip_sha256 and algorithm != HashAlgorithm.SHA256 else 1
    current_stage = 0

    if progress_callback:
        progress_callback(
            ProgressStats(
                "File Discovery", 1, 1, 0, total_files, start_time, time.time()
            )
        )

    # Stage 1: Exact dedupe by content
    if skip_sha256:
        log_action("Skipping SHA256 exact duplicate detection as requested")
        sha256_groups = []
        unique_files = []
        for chunk_files in scan_files_chunked(dirs, types, exclude_dirs, chunk_size):
            unique_files.extend(chunk_files)
        current_stage = 1
    else:
        current_stage += 1
        log_action("Stage 1: Computing SHA256 hashes for exact duplicate detection...")
        sha256_groups, unique_files = find_exact_duplicates_chunked(
            dirs,
            types,
            exclude_dirs,
            max_workers,
            chunk_size,
            progress_callback,
            start_time,
            current_stage,
            total_stages,
            total_files,
        )

    # Stage 2: Perceptual hashing for unique files (if algorithm requires it)
    if algorithm != HashAlgorithm.SHA256 and unique_files:
        current_stage += 1
        log_action(
            f"Stage 2: Computing {algorithm.value} hashes for {len(unique_files)} unique files..."
        )
        similarity_groups, hash_results_dict = find_similarity_duplicates_optimized(
            unique_files,
            similarity_threshold,
            algorithm,
            max_workers,
            chunk_size,
            progress_callback,
            start_time,
            current_stage,
            total_stages,
            total_files,
        )

        # Merge exact and similarity groups
        all_groups = sha256_groups + similarity_groups

        # Ensure SHA256-only groups also appear in the hash_results_dict for consistency
        for group in sha256_groups:
            for filepath in group:
                if filepath not in hash_results_dict:
                    hash_results_dict[filepath] = HashResult(
                        HashAlgorithm.SHA256,
                        "",
                        filepath,
                        get_file_type(filepath),
                        sha256_file(filepath),
                        0.0,
                    )
    else:
        # Only SHA256 stage completed (or no files to process in stage 2)
        all_groups = sha256_groups
        hash_results_dict = {}
        for group in sha256_groups:
            for filepath in group:
                hash_results_dict[filepath] = HashResult(
                    HashAlgorithm.SHA256,
                    "",
                    filepath,
                    get_file_type(filepath),
                    sha256_file(filepath),
                    0.0,
                )

    # Final progress callback to signal completion to caller/UI
    if progress_callback:
        total_time = time.time() - start_time
        progress_callback(
            ProgressStats(
                "Completed",
                total_stages,
                total_stages,
                total_files,
                total_files,
                start_time,
                time.time(),
                total_time,
            )
        )

    final_memory = MemoryStats.current()
    log_action(
        f"Optimized duplicate detection completed. Found {len(all_groups)} groups. "
        f"Memory usage: {final_memory.percent_used:.1f}% (peak reduction achieved)"
    )

    return all_groups, hash_results_dict


def find_similarity_groups_efficient(
    hash_results: List[HashResult], threshold: float, algorithm: HashAlgorithm
) -> List[List[str]]:
    """Brute-force (O(n²)) similarity grouping with memory-aware logging.

    This implementation is intended for smaller collections where an LSH strategy would be
    unnecessary complexity. It marks results as processed to avoid duplicate comparisons.
    """
    if len(hash_results) < 2:
        return []

    log_action(
        f"Finding similarity groups for {len(hash_results)} files with threshold {threshold}"
    )

    duplicate_groups = []
    processed = set()

    total_comparisons = (len(hash_results) * (len(hash_results) - 1)) // 2
    comparisons_done = 0

    for i, result1 in enumerate(hash_results):
        if result1.file_path in processed:
            continue

        similar_files = [result1.file_path]
        processed.add(result1.file_path)

        for j, result2 in enumerate(hash_results[i + 1 :], i + 1):
            comparisons_done += 1

            if result2.file_path in processed:
                continue

            similarity = calculate_hash_similarity(
                result1.hash_value, result2.hash_value, algorithm
            )
            if similarity <= threshold:
                similar_files.append(result2.file_path)
                processed.add(result2.file_path)
                # Store similarity score for display/ranking
                result2.similarity_score = similarity

            # Periodic progress logging for very large comparison counts
            if comparisons_done % 10000 == 0:
                progress_pct = (comparisons_done / total_comparisons) * 100
                current_memory = MemoryStats.current()
                log_action(
                    f"Similarity comparison progress: {progress_pct:.1f}% ({comparisons_done}/{total_comparisons}), Memory: {current_memory.percent_used:.1f}%"
                )

        if len(similar_files) > 1:
            duplicate_groups.append(similar_files)

    return duplicate_groups


def find_exact_duplicates_chunked(
    dirs: List[str],
    types: List[str],
    exclude_dirs: List[str],
    max_workers: int,
    chunk_size: int,
    progress_callback: Optional[callable] = None,
    start_time: float = 0,
    stage_num: int = 1,
    total_stages: int = 2,
    total_files: int = 0,
) -> Tuple[List[List[str]], List[str]]:
    """Compute SHA256 hashes in parallel over file chunks and group exact duplicates.

    Returns:
    - duplicate_groups: list of groups where each group has identical SHA256
    - unique_files: list of representative file paths (one per unique SHA256) to feed stage 2
    """
    phase_start = time.time()
    sha256_map = {}
    processed_files = 0

    # If caller did not provide total_files, compute it to support progress estimation.
    if total_files == 0:
        total_files = sum(
            1
            for d in dirs
            if os.path.exists(d)
            for root, _, filenames in os.walk(d)
            if not any(ex in root for ex in exclude_dirs)
            for fname in filenames
            if is_supported_file(fname, types)
        )

    # Iterate over filesystem chunks to bound peak memory usage
    chunk_count = 0
    for chunk_files in scan_files_chunked(dirs, types, exclude_dirs, chunk_size):
        chunk_hashes = {}
        chunk_count += 1

        # Compute SHA256 in a thread pool for IO-bound hashing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(sha256_file, f): f for f in chunk_files}

            for future in concurrent.futures.as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    sha256_hash = future.result()
                    if sha256_hash:  # Successful
                        chunk_hashes[filepath] = sha256_hash
                except Exception as e:
                    log_action(f"Error computing SHA256 for {filepath}: {e}")

        # Merge chunk results into global map keyed by hash
        for filepath, hash_value in chunk_hashes.items():
            sha256_map.setdefault(hash_value, []).append(filepath)

        processed_files += len(chunk_files)
        current_memory = MemoryStats.current()
        progress_pct = (processed_files / total_files) * 100

        # Estimate remaining time for operator feedback
        elapsed_time = time.time() - phase_start
        if processed_files > 0:
            estimated_total_time = (elapsed_time / processed_files) * total_files
            estimated_remaining = estimated_total_time - elapsed_time
        else:
            estimated_remaining = 0.0

        log_action(
            f"SHA256 Progress: {processed_files}/{total_files} files ({progress_pct:.1f}%), Memory: {current_memory.percent_used:.1f}%"
        )

        if progress_callback:
            progress_callback(
                ProgressStats(
                    f"Stage {stage_num}/{total_stages}: SHA256 Exact Duplicates",
                    chunk_count,
                    chunk_count + 1,  # approximate progress
                    processed_files,
                    total_files,
                    start_time or phase_start,
                    phase_start,
                    estimated_remaining,
                )
            )

        # Aggressively collect when memory is high to avoid OOM on large datasets
        if current_memory.percent_used > 85:
            log_action("High memory usage detected during SHA256 processing")
            gc.collect()

    # Build duplicate groups and unique file list for next stage
    duplicate_groups = [group for group in sha256_map.values() if len(group) > 1]
    unique_files = [group[0] for group in sha256_map.values() if len(group) == 1]

    total_exact_duplicates = sum(len(group) for group in duplicate_groups)
    log_action(
        f"Stage 1 complete: Found {len(duplicate_groups)} exact duplicate groups "
        f"({total_exact_duplicates} files). {len(unique_files)} files need similarity analysis."
    )

    return duplicate_groups, unique_files


def find_similarity_duplicates_optimized(
    unique_files: List[str],
    threshold: float,
    algorithm: HashAlgorithm,
    max_workers: int,
    chunk_size: int,
    progress_callback: Optional[callable] = None,
    start_time: float = 0,
    stage_num: int = 2,
    total_stages: int = 2,
    total_files: int = 0,
) -> Tuple[List[List[str]], Dict[str, "HashResult"]]:
    """
    Stage 2: compute perceptual hashes (with caching) and group similar files.
    """
    phase_start = time.time()
    cache = HashCache()
    cache.cleanup_old_entries(30)
    similarity_chunk_size = min(max(1, chunk_size // 2), 1000)
    all_hash_results = []
    processed_files = 0
    cached_hits = 0

    for i in range(0, len(unique_files), similarity_chunk_size):
        chunk_files = unique_files[i : i + similarity_chunk_size]
        chunk_hash_results = []

        # Always pass cache as keyword argument
        def _compute(fp):
            return compute_perceptual_hash(fp, algorithm=algorithm, cache=cache)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for res in executor.map(_compute, chunk_files):
                if res:
                    chunk_hash_results.append(res)
                    if res.error is None and cache:
                        pass

        all_hash_results.extend(chunk_hash_results)
        processed_files += len(chunk_files)
        current_memory = MemoryStats.current()
        progress_pct = (processed_files / len(unique_files)) * 100
        cache_hit_pct = (
            (cached_hits / processed_files) * 100 if processed_files > 0 else 0
        )
        elapsed_time = time.time() - phase_start
        if processed_files > 0:
            estimated_total = (elapsed_time / processed_files) * len(unique_files)
            estimated_remaining = max(0.0, estimated_total - elapsed_time)
        else:
            estimated_remaining = 0.0

        log_action(
            f"Similarity Progress: {processed_files}/{len(unique_files)} files ({progress_pct:.1f}%), "
            f"Cache hits: {cache_hit_pct:.1f}%, Memory: {current_memory.percent_used:.1f}%, ETA: {estimated_remaining:.1f}s"
        )

        if progress_callback:
            progress_callback(
                ProgressStats(
                    "Similarity Hashing",
                    i // similarity_chunk_size + 1,
                    (len(unique_files) + similarity_chunk_size - 1)
                    // similarity_chunk_size,
                    processed_files,
                    len(unique_files),
                    start_time,
                    time.time(),
                )
            )

        if current_memory.percent_used > 80:
            log_action(
                "High memory usage during similarity hashing, forcing a GC and brief sleep"
            )
            try:
                import gc

                gc.collect()
                time.sleep(0.1)
            except Exception:
                pass

    if len(all_hash_results) > 1000:
        duplicate_groups = find_similarity_groups_lsh(
            all_hash_results, threshold, algorithm
        )
    else:
        duplicate_groups = find_similarity_groups_efficient(
            all_hash_results, threshold, algorithm
        )

    hash_results_dict = {result.file_path: result for result in all_hash_results}
    cache.close()
    log_action(
        f"Stage 2 complete: Found {len(duplicate_groups)} similarity groups from {len(unique_files)} unique files. "
        f"Cache hit rate: {(cached_hits / len(unique_files)) * 100:.1f}%"
    )
    return duplicate_groups, hash_results_dict


def find_similarity_groups_lsh(
    hash_results: List[HashResult], threshold: float, algorithm: HashAlgorithm
) -> List[List[str]]:
    """LSH-based approximate grouping to avoid full O(n²) comparisons for big datasets.

    Approach summary:
    - Convert the start of each hex hash into a 64-bit integer and perform banding to bucket candidates.
    - Coarse filter with a fast approximate similarity function.
    - Perform final precise similarity checks on candidate groups.
    """
    from collections import defaultdict
    import struct

    if len(hash_results) < 2:
        return []

    log_action(
        f"Using LSH optimization with progressive thresholds for {len(hash_results)} files"
    )

    # Two-stage thresholds: coarse for bucketing, fine for final acceptance
    coarse_threshold = min(threshold * 2.0, 0.3)
    fine_threshold = threshold

    # LSH parameters chosen to balance bucket sizes and collision rates for coarse filtering.
    num_bands = 15
    rows_per_band = 4

    lsh_buckets = defaultdict(list)

    for result in hash_results:
        if not result.hash_value:
            continue

        try:
            # Use the first 16 hex chars (8 bytes) to create a 64-bit integer signature.
            if len(result.hash_value) >= 16:
                hash_bytes = bytes.fromhex(result.hash_value[:16])
                hash_int = struct.unpack(">Q", hash_bytes)[0]

                # Bit-sampling-based band signatures
                for band in range(num_bands):
                    band_signature = []
                    for row in range(rows_per_band):
                        bit_pos = (band * rows_per_band + row) % 64
                        bit_value = (hash_int >> bit_pos) & 1
                        band_signature.append(bit_value)

                    bucket_key = (band, tuple(band_signature))
                    lsh_buckets[bucket_key].append(result)

        except (ValueError, struct.error) as e:
            # If any hash can't be parsed to bytes, skip but log for debugging
            log_action(f"LSH processing error for {result.file_path}: {e}")
            continue

    # Coarse filtering within buckets followed by fine-grained pair checks
    duplicate_groups = []
    processed_files = set()

    bucket_comparisons = 0
    fine_comparisons = 0

    for bucket_files in lsh_buckets.values():
        if len(bucket_files) < 2:
            continue

        candidates = []
        for i, result1 in enumerate(bucket_files):
            if result1.file_path in processed_files:
                continue

            bucket_group = [result1]
            for result2 in bucket_files[i + 1 :]:
                bucket_comparisons += 1
                if result2.file_path in processed_files:
                    continue

                # Quick coarse similarity to weed out obvious mismatches
                coarse_similarity = calculate_hash_similarity_fast(
                    result1.hash_value, result2.hash_value, algorithm
                )
                if coarse_similarity <= coarse_threshold:
                    bucket_group.append(result2)

            if len(bucket_group) > 1:
                candidates.append(bucket_group)

        # Final precise comparisons on candidate groups
        for candidate_group in candidates:
            final_group = [candidate_group[0]]
            processed_files.add(candidate_group[0].file_path)

            for result in candidate_group[1:]:
                if result.file_path in processed_files:
                    continue

                fine_comparisons += 1
                precise_similarity = calculate_hash_similarity(
                    final_group[0].hash_value, result.hash_value, algorithm
                )
                if precise_similarity <= fine_threshold:
                    final_group.append(result)
                    processed_files.add(result.file_path)
                    result.similarity_score = precise_similarity

            if len(final_group) > 1:
                duplicate_groups.append([r.file_path for r in final_group])

    # Log some heuristics demonstrating the reduction achieved over naive O(n²)
    total_possible = len(hash_results) * (len(hash_results) - 1) // 2
    coarse_reduction = total_possible / max(bucket_comparisons, 1)
    fine_reduction = bucket_comparisons / max(fine_comparisons, 1)

    log_action(
        f"Progressive LSH: {bucket_comparisons} coarse + {fine_comparisons} fine comparisons vs {total_possible} naive"
    )
    log_action(
        f"Reduction factors: Coarse {coarse_reduction:.1f}x, Fine {fine_reduction:.1f}x, Total {(total_possible / max(fine_comparisons, 1)):.1f}x"
    )

    return duplicate_groups


def calculate_hash_similarity_fast(
    hash1: str, hash2: str, algorithm: HashAlgorithm
) -> float:
    """Very fast, approximate similarity metric used for coarse LSH filtering.

    Uses simple hex-string character differences to estimate Hamming distance.
    This is intentionally imprecise but very cheap compared to bit-level operations.
    """
    if not hash1 or not hash2 or hash1 == hash2:
        return 0.0 if hash1 == hash2 else 1.0

    if algorithm == HashAlgorithm.SHA256:
        return 0.0 if hash1 == hash2 else 1.0

    min_len = min(len(hash1), len(hash2))
    if min_len == 0:
        return 1.0

    differences = sum(c1 != c2 for c1, c2 in zip(hash1[:min_len], hash2[:min_len]))
    # Normalize roughly assuming 4 bits per hex character
    return min(differences / (min_len * 0.25), 1.0)


def rank_duplicates(
    dupe_group: List[str],
    path_preference: str = "shorter",
    filename_preference: str = None,
    quality_ranking: bool = False,
) -> List[str]:
    """Rank files in a duplicate group to select which to keep/delete.

    Criteria include:
    - Optional image quality metrics (sharpness/brightness/contrast)
    - Path and filename length preferences (user-configurable)
    - File modification time and size as tiebreakers
    """
    metas = []

    for f in dupe_group:
        meta = get_image_metadata(f)
        if meta:
            if quality_ranking and get_file_type(f) == FileType.IMAGE:
                try:
                    quality_score = calculate_image_quality(f)
                    meta["quality_score"] = quality_score
                except Exception as e:
                    log_action(f"Error calculating quality for {f}: {e}")
                    meta["quality_score"] = 0.0
            else:
                meta["quality_score"] = 0.0
            metas.append(meta)

    if not metas:
        return dupe_group

    def sort_key(m):
        quality = m.get("quality_score", 0.0)
        name_len = len(m.get("name", ""))
        path_len = len(m.get("path", ""))
        modified = m.get("modified", 0)
        size = m.get("size", 0)

        # Primary sort by quality if enabled (descending)
        if quality_ranking:
            primary = -quality
        else:
            primary = 0

        # Secondary preferences: file name length or path length etc.
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
    """Estimate image quality using OpenCV-based metrics.

    Combined metrics:
    - sharpness (Laplacian variance)
    - brightness (distance from mid-level)
    - contrast (stddev)
    Returns a value between 0.0 and 1.0.
    """
    if not cv2:
        # Can't compute without OpenCV; return neutral value to avoid bias.
        return 0.5

    try:
        img = cv2.imread(filepath)
        if img is None:
            return 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sharpness: Laplacian variance is a common heuristic for blur detection.
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 2000.0, 1.0)

        # Brightness score attempts to penalize extreme under/over exposure.
        mean_brightness = gray.mean()
        brightness_score = 1.0 - abs(mean_brightness - 128) / 128.0

        # Contrast normalized to plausible range
        contrast = gray.std()
        contrast_score = min(contrast / 64.0, 1.0)

        # Weighted combination tuned to prefer sharpness slightly more than brightness/contrast.
        quality_score = (
            sharpness_score * 0.5 + brightness_score * 0.3 + contrast_score * 0.2
        )

        return min(max(quality_score, 0.0), 1.0)

    except Exception as e:
        log_action(f"Error calculating image quality for {filepath}: {e}")
        return 0.5


import contextlib
import sys
import os

@contextlib.contextmanager
def suppress_stdout_stderr():
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yieldas devnull:
        finally:
            sys.stdout = old_stdouterr
            sys.stderr = old_stderr
