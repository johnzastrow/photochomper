#!/usr/bin/env bash
set -euo pipefail

# Delete files listed in a text file. Accepts Windows-style paths (C:\...) and
# converts them for use under a Windows bash (Git Bash / MSYS / Cygwin / WSL).
#
# Usage:
#   delete_photos_in_file.sh [--dry-run|-n] [--yes|-y] INPUT_FILE
#
# Examples:
#   delete_photos_in_file.sh --dry-run files_to_remove.txt
#   delete_photos_in_file.sh --yes files_to_remove.txt

usage() {
  cat <<EOF
Usage: $0 [--dry-run|-n] [--yes|-y] INPUT_FILE

Options:
  --dry-run, -n    Print actions without deleting
  --yes, -y        Delete without prompting
  --help, -h       Show this help
EOF
  exit 2
}

dry_run=0
assume_yes=0

while [[ $# -gt 0 && $1 == -* ]]; do
  case "$1" in
    -n|--dry-run) dry_run=1; shift;;
    -y|--yes) assume_yes=1; shift;;
    -h|--help) usage;;
    *) echo "Unknown option: $1" >&2; usage;;
  esac
done

if [[ $# -ne 1 ]]; then
  usage
fi


input_file="$1"

if [[ ! -f "$input_file" ]]; then
  echo "Input file not found: $input_file" >&2
  exit 2
fi

# Prepare timestamped audit logfile (format: YYYYMMDD-HHMMSS)
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
timestamp=$(date +"%Y%m%d-%H%M%S")
logfile="$script_dir/deleted_files_${timestamp}.log"
echo "Audit log: $logfile" >&2
echo "Deleted files log created at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "$logfile"

convert_path() {
  local raw="$1"

  # If cygpath is available prefer it for robust conversion
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -u -- "$raw" 2>/dev/null || echo "$raw"
    return
  fi

  # Replace backslashes with forward slashes
  local p=${raw//\\/\/}

  # Convert drive-letter paths like C:/ or C: to /c/ for Git Bash / MSYS style
  if [[ $p =~ ^([A-Za-z]):(.*) ]]; then
    local drive=${BASH_REMATCH[1]}
    local rest=${BASH_REMATCH[2]}
    rest=${rest#/}
    drive=$(echo "$drive" | tr '[:upper:]' '[:lower:]')
    echo "/${drive}/${rest}"
    return
  fi

  # If already looks like /c/ or /mnt/c/ or a UNC path, return as-is
  echo "$p"
}

delete_one() {
  local original="$1"
  local target
  target=$(convert_path "$original")

  # If converted path doesn't exist, try the original path as-is
  if [[ ! -e "$target" ]]; then
    # Some environments accept /mnt/c/... (WSL). Attempt common alternative:
    if [[ "$target" =~ ^/([a-z])/(.*) ]]; then
      local drv=${BASH_REMATCH[1]}
      local rest=${BASH_REMATCH[2]}
      if [[ -d "/mnt/$drv" ]]; then
        candidate="/mnt/$drv/$rest"
        if [[ -e "$candidate" ]]; then
          target="$candidate"
        fi
      fi
    fi
  fi

  if [[ ! -e "$target" ]]; then
    echo "Not found: $original -> $target" >&2
    return 1
  fi

  if [[ $dry_run -eq 1 ]]; then
    echo "DRY-RM: $target"
    echo "DRY-RM: $target" >> "$logfile"
    return 0
  fi

  if [[ $assume_yes -eq 0 ]]; then
    read -r -p "Delete '$target'? [y/N] " ans
    case "$ans" in
      [Yy]*) ;;
      *) echo "Skipped: $target"; return 0;;
    esac
  fi

  if rm -f -- "$target"; then
    echo "Deleted: $target"
    echo "Deleted: $target" >> "$logfile"
    return 0
  else
    echo "Failed to delete: $target" >&2
    echo "Failed to delete: $target" >> "$logfile"
    return 2
  fi
}

errors=0

# Read file line-by-line preserving whitespace
while IFS= read -r line || [[ -n $line ]]; do
  # Trim leading/trailing whitespace
  trimmed=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  # Skip empty lines and comments
  [[ -z "$trimmed" || ${trimmed:0:1} == '#' ]] && continue

  if ! delete_one "$trimmed"; then
    errors=$((errors+1))
  fi
done < "$input_file"

if [[ $errors -gt 0 ]]; then
  echo "Completed with $errors errors." >&2
  exit 3
fi

echo "Done." >&2
exit 0
