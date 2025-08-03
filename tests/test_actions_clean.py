#!/usr/bin/env python3
"""
Test script for the file actions system.
"""

import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.actions_clean import (
    ActionExecutor, FileAction, ActionType, ActionStatus,
    create_delete_actions, create_move_actions
)

def test_action_creation():
    """Test creation of actions from duplicate groups."""
    print("🔍 Testing Action Creation...")
    
    # Mock duplicate groups
    duplicate_groups = [
        ["/path/to/photo1.jpg", "/path/to/photo1_copy.jpg", "/path/to/photo1_dup.jpg"],
        ["/path/to/video1.mp4", "/path/to/video1_backup.mp4"],
        ["/path/to/doc.pdf", "/path/to/doc_old.pdf", "/path/to/doc_v2.pdf"]
    ]
    
    # Test delete action creation
    strategies = ["first", "last"]
    
    for strategy in strategies:
        delete_actions = create_delete_actions(duplicate_groups, strategy)
        total_deletes = sum(len(group) - 1 for group in duplicate_groups)
        
        print(f"  {strategy.capitalize()} strategy: {len(delete_actions)} delete actions (expected: {total_deletes})")
        
        # Show examples
        for action in delete_actions[:2]:
            print(f"    - Delete: {Path(action.source_path).name} (group {action.metadata['group_id']})")

def test_action_executor_basic():
    """Test basic ActionExecutor functionality."""
    print("\n🔧 Testing Basic Action Executor...")
    
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_test_"))
    
    try:
        # Create test file
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        
        # Initialize executor
        executor = ActionExecutor(str(test_dir / "backups"))
        
        # Test file backup
        backup_dir = executor.create_backup_dir("test")
        backup_path = executor.backup_file(str(test_file), backup_dir)
        
        print(f"  ✅ Created backup: {Path(backup_path).name}")
        
        # Test file integrity verification
        integrity_ok = executor.verify_file_integrity(str(test_file), backup_path)
        print(f"  {'✅' if integrity_ok else '❌'} Backup integrity: {integrity_ok}")
        
    finally:
        shutil.rmtree(test_dir)

def main():
    """Run action system tests."""
    print("⚡ PhotoChomper Action System Tests")
    print("=" * 40)
    
    try:
        test_action_creation()
        test_action_executor_basic()
        
        print("\n✅ Action system tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()