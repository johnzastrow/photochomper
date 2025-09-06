#!/bin/bash

# Check if a directory path is provided as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <directory_path>"
    exit 1
fi

target_directory="$1"

# Check if the provided path is a valid directory
if [ ! -d "$target_directory" ]; then
    echo "Error: '$target_directory' is not a valid directory."
    exit 1
fi

echo "Counting files in subdirectories of: $target_directory"

# Iterate through each subdirectory within the target directory
for dir in "$target_directory"/*/; do
    if [ -d "$dir" ]; then # Ensure it's a directory
        # Count files in the current subdirectory (excluding subdirectories themselves)
        file_count=$(find "$dir" -maxdepth 1 -type f | wc -l)
        # Extract just the directory name for cleaner output
        dir_name=$(basename "$dir")
        echo "$dir_name -: $file_count"
    fi
done