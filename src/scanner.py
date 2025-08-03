import os
import hashlib
from pathlib import Path
from typing import List

def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def is_image_file(filename: str, types: List[str]) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in [t.lower().lstrip(".") for t in types]

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