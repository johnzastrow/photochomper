#!/usr/bin/env python3
"""
Test script for the file actions system.
"""

import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.actions import (
    ActionExecutor, FileAction, ActionBatch, ActionType, ActionStatus,
    create_delete_actions, create_move_actions
)
from src.config import log_action

def create_test_files(test_dir: Path) -> list:
    """Create test files for action testing."""
    files = []
    
    # Create some test files
    for i in range(5):
        test_file = test_dir / f"test_file_{i}.txt"
        test_file.write_text(f"Test content {i}")
        files.append(str(test_file))
    
    # Create a subdirectory with files
    sub_dir = test_dir / "subdir"
    sub_dir.mkdir()
    
    for i in range(3):
        sub_file = sub_dir / f"sub_file_{i}.txt"
        sub_file.write_text(f"Sub content {i}")
        files.append(str(sub_file))
    
    return files

def test_action_executor():
    """Test the ActionExecutor class."""
    print("🔧 Testing Action Executor...")
    
    test_dir = Path(tempfile.mkdtemp(prefix="photochomper_actions_test_"))
    
    try:
        # Create test files
        test_files = create_test_files(test_dir)
        
        # Initialize executor
        executor = ActionExecutor(str(test_dir / "backups"))
        
        print(f"  📁 Created {len(test_files)} test files")
        
        # Test file backup
        print("\n  💾 Testing file backup...")\n        backup_dir = executor.create_backup_dir(\"test_backup\")\n        \n        backup_path = executor.backup_file(test_files[0], backup_dir)\n        print(f\"    ✅ Backed up {Path(test_files[0]).name} to {backup_path}\")\n        \n        # Verify backup integrity\n        integrity_ok = executor.verify_file_integrity(test_files[0], backup_path)\n        print(f\"    {'✅' if integrity_ok else '❌'} Backup integrity: {integrity_ok}\")\n        \n        # Test individual actions\n        print(\"\\n  ⚡ Testing individual actions...\")\n        \n        # Test copy action\n        copy_target = test_dir / \"copied_file.txt\"\n        copy_action = FileAction(\n            action_id=\"test_copy\",\n            action_type=ActionType.COPY,\n            source_path=test_files[1],\n            target_path=str(copy_target)\n        )\n        \n        success = executor.execute_action(copy_action, backup_dir)\n        print(f\"    {'✅' if success else '❌'} Copy action: {copy_action.status.value}\")\n        \n        # Test move action\n        move_target = test_dir / \"moved_file.txt\"\n        move_action = FileAction(\n            action_id=\"test_move\",\n            action_type=ActionType.MOVE,\n            source_path=test_files[2],\n            target_path=str(move_target)\n        )\n        \n        success = executor.execute_action(move_action, backup_dir)\n        print(f\"    {'✅' if success else '❌'} Move action: {move_action.status.value}\")\n        \n        # Test delete action\n        delete_action = FileAction(\n            action_id=\"test_delete\",\n            action_type=ActionType.DELETE,\n            source_path=test_files[3]\n        )\n        \n        success = executor.execute_action(delete_action, backup_dir)\n        print(f\"    {'✅' if success else '❌'} Delete action: {delete_action.status.value}\")\n        \n        # Test rollback\n        print(\"\\n  ↩️  Testing rollback...\")\n        \n        # Create a batch with the actions\n        batch = ActionBatch(\n            batch_id=\"test_rollback\",\n            actions=[copy_action, move_action, delete_action],\n            backup_dir=str(backup_dir),\n            created_at=datetime.now().isoformat()\n        )\n        \n        rollback_success = executor.rollback_batch(batch)\n        print(f\"    {'✅' if rollback_success else '❌'} Rollback completed: {rollback_success}\")\n        \n        # Check if files were restored\n        restored_files = [\n            Path(test_files[2]).exists(),  # Should be restored from move\n            Path(test_files[3]).exists(),  # Should be restored from delete\n        ]\n        \n        print(f\"    📋 Files restored: {sum(restored_files)}/{len(restored_files)}\")\n        \n    finally:\n        # Cleanup\n        shutil.rmtree(test_dir)\n\ndef test_batch_operations():\n    \"\"\"Test batch action operations.\"\"\"\n    print(\"\\n📦 Testing Batch Operations...\")\n    \n    test_dir = Path(tempfile.mkdtemp(prefix=\"photochomper_batch_test_\"))\n    \n    try:\n        # Create test files\n        test_files = create_test_files(test_dir)\n        \n        # Initialize executor\n        executor = ActionExecutor(str(test_dir / \"backups\"))\n        \n        # Create a batch of actions\n        actions = []\n        \n        # Copy actions\n        for i, source_file in enumerate(test_files[:3]):\n            target_file = test_dir / \"copies\" / f\"copy_{i}_{Path(source_file).name}\"\n            action = FileAction(\n                action_id=f\"batch_copy_{i}\",\n                action_type=ActionType.COPY,\n                source_path=source_file,\n                target_path=str(target_file)\n            )\n            actions.append(action)\n        \n        # Move actions\n        for i, source_file in enumerate(test_files[3:5]):\n            target_file = test_dir / \"moved\" / f\"moved_{i}_{Path(source_file).name}\"\n            action = FileAction(\n                action_id=f\"batch_move_{i}\",\n                action_type=ActionType.MOVE,\n                source_path=source_file,\n                target_path=str(target_file)\n            )\n            actions.append(action)\n        \n        batch = ActionBatch(\n            batch_id=\"test_batch_operations\",\n            actions=actions,\n            backup_dir=\"\",  # Will be set by executor\n            created_at=datetime.now().isoformat()\n        )\n        \n        print(f\"  📋 Created batch with {len(actions)} actions\")\n        \n        # Progress callback for testing\n        def progress_callback(current, total, percent, action):\n            print(f\"    Progress: {current}/{total} ({percent:.1f}%) - {action.action_type.value} {Path(action.source_path).name}\")\n        \n        # Execute batch\n        result_batch = executor.execute_batch(batch, progress_callback)\n        \n        print(f\"\\n  📊 Batch Results:\")\n        print(f\"    Completed: {result_batch.completed_actions}\")\n        print(f\"    Failed: {result_batch.failed_actions}\")\n        print(f\"    Success Rate: {(result_batch.completed_actions/result_batch.total_actions)*100:.1f}%\")\n        \n        # Test batch metadata save/load\n        print(\"\\n  💾 Testing batch metadata persistence...\")\n        \n        loaded_batch = executor.load_batch_metadata(result_batch.backup_dir)\n        if loaded_batch:\n            print(f\"    ✅ Loaded batch: {loaded_batch.batch_id} with {len(loaded_batch.actions)} actions\")\n        else:\n            print(f\"    ❌ Failed to load batch metadata\")\n        \n    finally:\n        # Cleanup\n        shutil.rmtree(test_dir)\n\ndef test_duplicate_action_creation():\n    \"\"\"Test creation of actions from duplicate groups.\"\"\"\n    print(\"\\n🔍 Testing Duplicate Action Creation...\")\n    \n    # Mock duplicate groups\n    duplicate_groups = [\n        [\"/path/to/photo1.jpg\", \"/path/to/photo1_copy.jpg\", \"/path/to/photo1_dup.jpg\"],\n        [\"/path/to/video1.mp4\", \"/path/to/video1_backup.mp4\"],\n        [\"/path/to/doc.pdf\", \"/path/to/doc_old.pdf\", \"/path/to/doc_v2.pdf\"]\n    ]\n    \n    # Test delete action creation\n    print(\"  🗑️  Testing delete action creation...\")\n    \n    strategies = [\"first\", \"last\", \"largest\", \"smallest\"]\n    \n    for strategy in strategies:\n        delete_actions = create_delete_actions(duplicate_groups, strategy)\n        total_deletes = sum(len(group) - 1 for group in duplicate_groups)  # Keep one from each group\n        \n        print(f\"    {strategy.capitalize()} strategy: {len(delete_actions)} delete actions (expected: {total_deletes})\")\n        \n        # Show some examples\n        for action in delete_actions[:2]:\n            print(f\"      - Delete: {Path(action.source_path).name} (group {action.metadata['group_id']})\")\n    \n    # Test move action creation\n    print(\"\\n  📦 Testing move action creation...\")\n    \n    temp_dir = tempfile.mkdtemp(prefix=\"photochomper_move_test_\")\n    \n    try:\n        move_actions = create_move_actions(duplicate_groups, temp_dir, \"first\")\n        total_moves = sum(len(group) - 1 for group in duplicate_groups)\n        \n        print(f\"    Created {len(move_actions)} move actions (expected: {total_moves})\")\n        \n        # Show some examples\n        for action in move_actions[:2]:\n            source_name = Path(action.source_path).name\n            target_name = Path(action.target_path).name\n            print(f\"      - Move: {source_name} -> {target_name}\")\n    \n    finally:\n        # Cleanup\n        shutil.rmtree(temp_dir)\n\ndef main():\n    \"\"\"Run all action system tests.\"\"\"\n    print(\"⚡ PhotoChomper Action System Tests\")\n    print(\"=\" * 40)\n    \n    try:\n        test_action_executor()\n        test_batch_operations()\n        test_duplicate_action_creation()\n        \n        print(\"\\n✅ All action system tests completed successfully!\")\n        \n    except Exception as e:\n        print(f\"\\n❌ Action system test failed: {e}\")\n        import traceback\n        traceback.print_exc()\n\nif __name__ == \"__main__\":\n    main()