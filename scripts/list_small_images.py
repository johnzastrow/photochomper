#!/usr/bin/env python3
"""
List full paths of JPEG and PNG files smaller than a given size in any dimension.

Usage:
  python scripts/list_small_images.py SIZE [--dir DIR] [--no-recursive]

Examples:
  python scripts/list_small_images.py 800
  python scripts/list_small_images.py 600 --dir /path/to/photos

This script prints absolute file paths, one per line, for files whose width OR
height is smaller than the provided SIZE (pixels).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

try:
    from PIL import Image
except Exception:
    print("Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(2)


def iter_image_files(root: str, recursive: bool = True) -> Iterable[str]:
    root = os.path.expanduser(root)
    if recursive:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                yield os.path.join(dirpath, fn)
    else:
        for fn in os.listdir(root):
            path = os.path.join(root, fn)
            if os.path.isfile(path):
                yield path


def is_target_ext(name: str) -> bool:
    name = name.lower()
    return name.endswith(('.jpg', '.jpeg', '.png'))


def main() -> int:
    p = argparse.ArgumentParser(description="List JPEG/PNG files smaller than SIZE in any dimension")
    p.add_argument('size', type=int, help='Size in pixels; files with width OR height < SIZE are listed')
    p.add_argument('--dir', '-d', default='.', help='Directory to scan (default: current directory)')
    p.add_argument('--no-recursive', action='store_true', help='Do not recurse into subdirectories')
    p.add_argument('--quiet-errors', action='store_true', help='Suppress errors while opening files')
    args = p.parse_args()

    size = args.size
    if size <= 0:
        print('Size must be a positive integer', file=sys.stderr)
        return 2

    found = 0
    for path in iter_image_files(args.dir, recursive=not args.no_recursive):
        if not is_target_ext(path):
            continue
        try:
            with Image.open(path) as img:
                w, h = img.size
        except Exception as e:
            if not args.quiet_errors:
                print(f'Warning: could not open {path}: {e}', file=sys.stderr)
            continue

        if w < size or h < size:
            print(os.path.abspath(path))
            found += 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())