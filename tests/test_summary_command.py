#!/usr/bin/env python3
"""
Test script for the --summary command functionality.
"""

import os
import json
import csv
import tempfile
from pathlib import Path
from datetime import datetime

def create_mock_csv_report(filename: str):
    """Create a mock CSV report file for testing."""
    data = [
        {
            "GroupID": "0",
            "Master": "/home/user/photos/photo1.jpg",
            "MasterPath": "/home/user/photos",
            "MasterName": "photo1.jpg",
            "MasterSize": "2048000",
            "MasterCreated": "1640995200",
            "MasterModified": "1640995200",
            "DuplicateName": "photo1_copy.jpg",
            "DuplicatePath": "/home/user/backup/photo1_copy.jpg",
            "DuplicateSize": "2048000", 
            "ConfidenceScore": "1.0",
            "Reasons": "same_size|same_hash"
        },
        {
            "GroupID": "1", 
            "Master": "/home/user/photos/photo2.jpg",
            "MasterPath": "/home/user/photos",
            "MasterName": "photo2.jpg",
            "MasterSize": "1536000",
            "MasterCreated": "1640995300",
            "MasterModified": "1640995300",
            "DuplicateName": "photo2_dup.jpg",
            "DuplicatePath": "/home/user/downloads/photo2_dup.jpg",
            "DuplicateSize": "1536000",
            "ConfidenceScore": "0.95",
            "Reasons": "same_size|similar_content"
        }
    ]
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Created mock CSV report: {filename}")

def create_mock_json_report(filename: str):
    """Create a mock JSON report file for testing."""
    data = [
        {
            "group_id": 0,
            "master": "/home/user/photos/video1.mp4",
            "master_attributes": {
                "name": "video1.mp4",
                "path": "/home/user/photos/video1.mp4",
                "size": 52428800,
                "created": "1640995400",
                "modified": "1640995400",
                "width": 1920,
                "height": 1080,
                "file_type": "mp4"
            },
            "duplicates": [
                {
                    "file": "/home/user/backup/video1_backup.mp4",
                    "score": 1.0,
                    "reasons": "same_size|same_hash",
                    "name": "video1_backup.mp4",
                    "path": "/home/user/backup/video1_backup.mp4",
                    "size": 52428800,
                    "width": 1920,
                    "height": 1080,
                    "file_type": "mp4"
                }
            ]
        }
    ]
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Created mock JSON report: {filename}")

def test_summary_command():
    """Test the --summary command with mock data."""
    print("📋 Testing --summary Command")
    print("=" * 40)
    
    # Create temporary test files
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_summary_test_"))
    old_cwd = os.getcwd()
    
    try:
        # Change to test directory
        os.chdir(test_dir)
        
        # Create mock report files
        csv_file = "duplicates_report_20240101_120000.csv"
        json_file = "duplicates_report_20240101_130000.json"
        
        create_mock_csv_report(csv_file)
        create_mock_json_report(json_file)
        
        print("\n🔍 Files created in test directory:")
        for f in os.listdir('.'):
            print(f"  • {f}")
        
        print("\n📖 Usage Examples:")
        print("Now you can test the --summary command:")
        print(f"  cd {test_dir}")
        print(f"  python {old_cwd}/main.py --summary")
        print(f"  python {old_cwd}/main.py --summary {csv_file}")
        print(f"  python {old_cwd}/main.py --summary {csv_file} {json_file}")
        
        print(f"\n📁 Test files are in: {test_dir}")
        print("Note: Files will be cleaned up when the test directory is removed")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        
    finally:
        # Return to original directory  
        os.chdir(old_cwd)
        
        # Note: We don't clean up the temp dir automatically so you can test
        print(f"\n💡 Tip: Remove test directory when done: rm -rf {test_dir}")

def show_summary_command_help():
    """Show help information for the --summary command."""
    print("\n📚 --summary Command Usage")
    print("=" * 30)
    print()
    print("The --summary command generates markdown summaries from existing")
    print("CSV and JSON duplicate reports without re-scanning for duplicates.")
    print()
    print("📋 Basic Usage:")
    print("  python main.py --summary                    # Auto-discover reports")
    print("  python main.py --summary report.csv         # Use specific file")
    print("  python main.py --summary *.csv *.json       # Use multiple files")
    print()
    print("🔍 Auto-discovery looks for files matching:")
    print("  • duplicates_report*.csv")
    print("  • duplicates_report*.json")
    print("  • *_report*.csv")
    print("  • *_report*.json")
    print()
    print("📄 Output:")
    print("  • Creates duplicates_summary_YYYYMMDD_HHMMSS.md")
    print("  • Includes statistics, directory analysis, and file type breakdown")
    print("  • Shows confidence score ranges and duplicate reasons")
    print()
    print("⚡ Workflow:")
    print("  1. Run --search to generate CSV/JSON reports")
    print("  2. Run --summary to create markdown summaries")
    print("  3. View the .md file in any markdown viewer")

def main():
    """Run summary command tests and show usage information."""
    print("⚡ PhotoChomper --summary Command Test")
    print("=" * 50)
    
    try:
        show_summary_command_help()
        test_summary_command()
        
        print("\n✅ Summary command test setup completed!")
        
    except Exception as e:
        print(f"\n❌ Summary command test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()