import os
import sys


def get_unique_file_extensions(root_dir):
    extensions = set()
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext:
                extensions.add(ext.lower())
    return sorted(extensions)


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    unique_extensions = get_unique_file_extensions(root)
    print("Unique file extensions found:")
    for ext in unique_extensions:
        print(ext)
        else:
            if len(sys.argv) > 1:
                root = sys.argv[1]
            else:
                root = os.path.dirname(os.path.abspath(__file__))
            unique_extensions = get_unique_file_extensions(root)
            print("Unique file extensions found:")
            for ext in unique_extensions:
                print(ext)