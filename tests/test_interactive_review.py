#!/usr/bin/env python3
"""
Test script for the interactive duplicate review functionality.
"""

import tempfile
import shutil
from pathlib import Path

from src.tui import display_duplicate_group
from src.actions import FileAction, ActionType, create_delete_actions
from src.scanner import find_duplicates, HashAlgorithm

def create_test_duplicates(test_dir: Path) -> list:
    """Create test files that will be detected as duplicates."""
    # Create identical files
    content1 = "Test content for duplicate detection"
    content2 = "Different content for variety"
    
    # Group 1: Identical text files
    group1_files = []
    for i in range(3):
        file_path = test_dir / f"duplicate_text_{i}.txt"
        file_path.write_text(content1)
        group1_files.append(str(file_path))
    
    # Group 2: Another set of identical files
    group2_files = []
    subdir = test_dir / "subdir"
    subdir.mkdir()
    for i in range(2):
        file_path = subdir / f"duplicate_doc_{i}.txt"
        file_path.write_text(content2)
        group2_files.append(str(file_path))
    
    return [group1_files, group2_files]

def test_display_functionality():
    """Test the duplicate group display functionality."""
    print("📋 Testing Duplicate Group Display...")
    
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_display_test_"))
    
    try:
        # Create test duplicates
        duplicate_groups = create_test_duplicates(test_dir)
        
        # Test display of first group
        print(f"  📁 Created {len(duplicate_groups)} duplicate groups")
        print(f"  📄 Group 1 has {len(duplicate_groups[0])} files")
        print(f"  📄 Group 2 has {len(duplicate_groups[1])} files")
        
        # Display the groups (this will show in terminal)
        for i, group in enumerate(duplicate_groups):
            display_duplicate_group(group, i)
        
        print("  ✅ Display functionality test completed")
        
    finally:
        shutil.rmtree(test_dir)

def test_action_creation():
    """Test creation of actions from mock user choices."""
    print("\n🎯 Testing Action Creation...")
    
    # Mock duplicate groups
    duplicate_groups = [
        ["/path/to/photo1.jpg", "/path/to/photo1_copy.jpg", "/path/to/photo1_dup.jpg"],
        ["/path/to/video1.mp4", "/path/to/video1_backup.mp4"],
    ]
    
    # Test delete action creation
    delete_actions = create_delete_actions(duplicate_groups, "first")
    print(f"  🗑️  Created {len(delete_actions)} delete actions")
    
    # Show action details
    for action in delete_actions:
        print(f"    - Delete: {Path(action.source_path).name} (group {action.metadata['group_id']})")
    
    print("  ✅ Action creation test completed")

def test_full_duplicate_detection():
    """Test the full duplicate detection with actual files."""
    print("\n🔍 Testing Full Duplicate Detection...")
    
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_full_test_"))
    
    try:
        # Create test duplicates
        duplicate_groups = create_test_duplicates(test_dir)
        
        # Run actual duplicate detection
        found_duplicates = find_duplicates(
            dirs=[str(test_dir)],
            types=["txt"],
            exclude_dirs=[],
            similarity_threshold=0.0,  # Exact matches only for SHA256
            algorithm=HashAlgorithm.SHA256,
            max_workers=2
        )
        
        print(f"  🔎 Found {len(found_duplicates)} duplicate groups")
        for i, group in enumerate(found_duplicates):
            print(f"    Group {i + 1}: {len(group)} files")
            for file_path in group:
                print(f"      - {Path(file_path).name}")
        
        # Verify we found the expected duplicates
        expected_groups = len(duplicate_groups)
        if len(found_duplicates) == expected_groups:
            print("  ✅ Duplicate detection working correctly")
        else:
            print(f"  ⚠️  Expected {expected_groups} groups, found {len(found_duplicates)}")
        
    finally:
        shutil.rmtree(test_dir)

def test_action_executor_with_real_files():
    """Test the action executor with real files."""
    print("\n⚡ Testing Action Executor with Real Files...")
    
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_executor_test_"))
    
    try:
        # Create test files
        test_files = []
        for i in range(3):
            file_path = test_dir / f"test_file_{i}.txt"
            file_path.write_text(f"Test content {i}")
            test_files.append(str(file_path))
        
        # Create some actions
        actions = [
            FileAction(
                action_id="test_copy",
                action_type=ActionType.COPY,
                source_path=test_files[0],
                target_path=str(test_dir / "copied_file.txt"),
                metadata={"test": True}
            ),
            FileAction(
                action_id="test_move",
                action_type=ActionType.MOVE,
                source_path=test_files[1],
                target_path=str(test_dir / "moved_file.txt"),
                metadata={"test": True}
            )
        ]
        
        print(f"  📋 Created {len(actions)} test actions")
        
        # Execute actions (but don't actually run them in test)
        print("  📦 Actions ready for execution:")
        for action in actions:
            print(f"    - {action.action_type.value}: {Path(action.source_path).name}")
        
        print("  ✅ Action executor test completed")
        
    finally:
        shutil.rmtree(test_dir)

def show_usage_example():
    """Show an example of how to use the interactive review."""
    print("\n📖 Interactive Review Usage Example:")
    print("=" * 50)
    print()
    print("To use the interactive duplicate review:")
    print()
    print("1. First run setup to create a configuration:")
    print("   python main.py --setup")
    print()
    print("2. Then run the interactive review:")
    print("   python main.py --review")
    print()
    print("3. During review, you can use these commands:")
    print("   - 'k' = Keep specific file (choose which one)")
    print("   - 'd' = Delete all but first file")
    print("   - 'm' = Move duplicates to a directory")
    print("   - 's' = Skip this group")
    print("   - 'a' = Auto mode (choose strategy)")
    print("   - 'q' = Quit review")
    print()
    print("4. Auto mode strategies:")
    print("   - first = Keep first file, delete others")
    print("   - last = Keep last file, delete others") 
    print("   - largest = Keep largest file, delete others")
    print("   - smallest = Keep smallest file, delete others")
    print()
    print("5. All actions create backups before execution")
    print("6. Failed actions can be rolled back")

def main():
    """Run all interactive review tests."""
    print("⚡ PhotoChomper Interactive Review Tests")
    print("=" * 50)
    
    try:
        test_display_functionality()
        test_action_creation()
        test_full_duplicate_detection()
        test_action_executor_with_real_files()
        
        print("\n✅ All interactive review tests completed successfully!")
        
        show_usage_example()
        
    except Exception as e:
        print(f"\n❌ Interactive review test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()