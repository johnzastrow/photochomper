"""
File action execution system for PhotoChomper.

This module provides safe, recoverable file operations including:
- Delete operations with backup
- Move/rename operations  
- Batch processing with progress tracking
- Rollback capabilities for error recovery
"""

import os
import shutil
import hashlib
import json
from datetime import datetime  
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from src.config import log_action

class ActionType(Enum):
    """Types of file actions that can be performed."""
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"
    TAG = "tag"  # Add metadata tags to files

class ActionStatus(Enum):
    """Status of action execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class FileAction:
    """Represents a single file action to be performed."""
    action_id: str
    action_type: ActionType
    source_path: str
    target_path: Optional[str] = None
    backup_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    status: ActionStatus = ActionStatus.PENDING
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ActionBatch:
    """Container for batch file operations with rollback support."""
    batch_id: str
    actions: List[FileAction]
    backup_dir: str
    created_at: str
    completed_at: Optional[str] = None
    total_actions: int = 0
    completed_actions: int = 0
    failed_actions: int = 0
    
    def __post_init__(self):
        if self.total_actions == 0:
            self.total_actions = len(self.actions)

class ActionExecutor:
    """Executes file actions with backup and rollback capabilities."""
    
    def __init__(self, backup_base_dir: str = "photochomper_backups"):
        self.backup_base_dir = Path(backup_base_dir)
        self.backup_base_dir.mkdir(exist_ok=True)
        
    def create_backup_dir(self, batch_id: str) -> Path:
        """Create a unique backup directory for a batch of operations."""
        backup_dir = self.backup_base_dir / f"batch_{batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
        
    def backup_file(self, source_path: str, backup_dir: Path) -> str:
        """Create a backup copy of a file before modification."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Create backup with original directory structure
        relative_path = source.relative_to(source.anchor) if source.is_absolute() else source
        backup_path = backup_dir / "originals" / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file with metadata preservation
        shutil.copy2(source, backup_path)
        
        # Verify backup integrity
        if not self.verify_file_integrity(str(source), str(backup_path)):
            raise RuntimeError(f"Backup verification failed for {source_path}")
        
        log_action(f"Backed up {source_path} to {backup_path}")
        return str(backup_path)
    
    def verify_file_integrity(self, file1: str, file2: str) -> bool:
        """Verify two files have identical content using checksums."""
        try:
            hash1 = self.calculate_file_hash(file1)
            hash2 = self.calculate_file_hash(file2)
            return hash1 == hash2
        except Exception as e:
            log_action(f"Error verifying file integrity: {e}")
            return False
    
    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA-256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def execute_action(self, action: FileAction, backup_dir: Path) -> bool:
        """Execute a single file action with error handling."""
        try:
            action.status = ActionStatus.IN_PROGRESS
            source = Path(action.source_path)
            
            if action.action_type == ActionType.DELETE:
                # Backup before deletion
                action.backup_path = self.backup_file(action.source_path, backup_dir)
                
                # Perform deletion
                if source.is_file():
                    source.unlink()
                elif source.is_dir():
                    shutil.rmtree(source)
                else:
                    raise FileNotFoundError(f"File not found: {action.source_path}")
                
                log_action(f"Deleted {action.source_path}")
                
            elif action.action_type == ActionType.MOVE:
                if not action.target_path:
                    raise ValueError("Target path required for move operation")
                
                target = Path(action.target_path)
                
                # Backup source file
                action.backup_path = self.backup_file(action.source_path, backup_dir)
                
                # Create target directory if needed
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Perform move
                shutil.move(source, target)
                
                log_action(f"Moved {action.source_path} to {action.target_path}")
                
            elif action.action_type == ActionType.COPY:
                if not action.target_path:
                    raise ValueError("Target path required for copy operation")
                
                target = Path(action.target_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Perform copy
                if source.is_file():
                    shutil.copy2(source, target)
                elif source.is_dir():
                    shutil.copytree(source, target)
                
                log_action(f"Copied {action.source_path} to {action.target_path}")
                
            elif action.action_type == ActionType.RENAME:
                if not action.target_path:
                    raise ValueError("Target path required for rename operation")
                
                target = Path(action.target_path)
                
                # Backup before rename
                action.backup_path = self.backup_file(action.source_path, backup_dir)
                
                # Perform rename
                source.rename(target)
                
                log_action(f"Renamed {action.source_path} to {action.target_path}")
                
            elif action.action_type == ActionType.TAG:
                # For tagging, we might write metadata to sidecar files or EXIF
                # This is a placeholder for future metadata tagging implementation
                log_action(f"Tagged {action.source_path} with metadata: {action.metadata}")
                
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")
            
            action.status = ActionStatus.COMPLETED
            return True
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error_message = str(e)
            log_action(f"Action failed for {action.source_path}: {e}")
            return False
    
    def execute_batch(self, batch: ActionBatch, progress_callback=None) -> ActionBatch:
        """Execute a batch of file actions with progress tracking."""
        backup_dir = self.create_backup_dir(batch.batch_id)
        batch.backup_dir = str(backup_dir)
        
        # Save batch metadata
        self.save_batch_metadata(batch, backup_dir)
        
        log_action(f"Starting batch execution: {batch.batch_id} ({len(batch.actions)} actions)")
        
        for i, action in enumerate(batch.actions):
            success = self.execute_action(action, backup_dir)
            
            if success:
                batch.completed_actions += 1
            else:
                batch.failed_actions += 1
            
            # Call progress callback if provided
            if progress_callback:
                progress_pct = ((i + 1) / batch.total_actions) * 100
                progress_callback(i + 1, batch.total_actions, progress_pct, action)
        
        batch.completed_at = datetime.now().isoformat()
        
        # Update batch metadata
        self.save_batch_metadata(batch, backup_dir)
        
        log_action(f"Batch execution completed: {batch.completed_actions} successful, {batch.failed_actions} failed")
        
        return batch
    
    def rollback_batch(self, batch: ActionBatch) -> bool:
        """Rollback a batch of actions using backup files."""
        if not batch.backup_dir or not Path(batch.backup_dir).exists():
            log_action(f"Cannot rollback batch {batch.batch_id}: backup directory not found")
            return False
        
        backup_dir = Path(batch.backup_dir)
        rollback_count = 0
        
        log_action(f"Starting rollback for batch {batch.batch_id}")
        
        for action in batch.actions:
            if action.status != ActionStatus.COMPLETED:
                continue
                
            try:
                if action.action_type == ActionType.DELETE:
                    # Restore from backup
                    if action.backup_path and Path(action.backup_path).exists():
                        shutil.copy2(action.backup_path, action.source_path)
                        log_action(f"Restored {action.source_path} from backup")
                        rollback_count += 1
                        
                elif action.action_type == ActionType.MOVE:
                    # Move back to original location
                    if action.target_path and Path(action.target_path).exists():
                        shutil.move(action.target_path, action.source_path)
                        log_action(f"Moved {action.target_path} back to {action.source_path}")
                        rollback_count += 1
                        
                elif action.action_type == ActionType.RENAME:
                    # Rename back to original
                    if action.target_path and Path(action.target_path).exists():
                        Path(action.target_path).rename(action.source_path)
                        log_action(f"Renamed {action.target_path} back to {action.source_path}")
                        rollback_count += 1
                        
                elif action.action_type == ActionType.COPY:
                    # Remove the copy
                    if action.target_path and Path(action.target_path).exists():
                        target = Path(action.target_path)
                        if target.is_file():
                            target.unlink()
                        elif target.is_dir():
                            shutil.rmtree(target)
                        log_action(f"Removed copy {action.target_path}")
                        rollback_count += 1
                
                action.status = ActionStatus.ROLLED_BACK
                
            except Exception as e:
                log_action(f"Failed to rollback action for {action.source_path}: {e}")
        
        log_action(f"Rollback completed: {rollback_count} actions rolled back")
        return rollback_count > 0
    
    def save_batch_metadata(self, batch: ActionBatch, backup_dir: Path):
        """Save batch metadata to JSON file for recovery purposes."""
        metadata_file = backup_dir / "batch_metadata.json"
        
        # Convert batch to dictionary for JSON serialization
        batch_dict = asdict(batch)
        
        # Convert enums to strings
        for action_dict in batch_dict['actions']:
            if 'action_type' in action_dict:
                action_dict['action_type'] = action_dict['action_type'].value if hasattr(action_dict['action_type'], 'value') else str(action_dict['action_type'])
            if 'status' in action_dict:
                action_dict['status'] = action_dict['status'].value if hasattr(action_dict['status'], 'value') else str(action_dict['status'])
        
        with open(metadata_file, 'w') as f:
            json.dump(batch_dict, f, indent=2)
    
    def load_batch_metadata(self, backup_dir: str) -> Optional[ActionBatch]:
        """Load batch metadata from backup directory."""
        metadata_file = Path(backup_dir) / "batch_metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                batch_dict = json.load(f)
            
            # Convert back to proper types
            actions = []
            for action_dict in batch_dict['actions']:
                action_dict['action_type'] = ActionType(action_dict['action_type'])
                action_dict['status'] = ActionStatus(action_dict['status'])
                actions.append(FileAction(**action_dict))
            
            batch_dict['actions'] = actions
            return ActionBatch(**batch_dict)
            
        except Exception as e:
            log_action(f"Error loading batch metadata: {e}")
            return None

def create_delete_actions(duplicate_groups: List[List[str]], keep_strategy: str = "first") -> List[FileAction]:
    """Create delete actions for duplicate files based on keep strategy."""
    actions = []
    
    for group_id, group in enumerate(duplicate_groups):
        if len(group) < 2:
            continue
            
        # Determine which file to keep
        if keep_strategy == "first":
            files_to_delete = group[1:]
        elif keep_strategy == "last":
            files_to_delete = group[:-1]
        elif keep_strategy == "largest":
            # Keep the largest file
            files_with_size = [(f, os.path.getsize(f)) for f in group if os.path.exists(f)]
            files_with_size.sort(key=lambda x: x[1], reverse=True)
            files_to_delete = [f[0] for f in files_with_size[1:]]
        elif keep_strategy == "smallest":
            # Keep the smallest file
            files_with_size = [(f, os.path.getsize(f)) for f in group if os.path.exists(f)]
            files_with_size.sort(key=lambda x: x[1])
            files_to_delete = [f[0] for f in files_with_size[1:]]
        else:
            # Default: keep first
            files_to_delete = group[1:]
        
        # Create delete actions
        for file_path in files_to_delete:
            action_id = f"delete_{group_id}_{len(actions)}"
            action = FileAction(
                action_id=action_id,
                action_type=ActionType.DELETE,
                source_path=file_path,
                metadata={"group_id": group_id, "keep_strategy": keep_strategy}
            )
            actions.append(action)
    
    return actions

def create_move_actions(duplicate_groups: List[List[str]], target_dir: str, 
                       keep_strategy: str = "first") -> List[FileAction]:
    """Create move actions to relocate duplicate files to a target directory."""
    actions = []
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    for group_id, group in enumerate(duplicate_groups):
        if len(group) < 2:
            continue
            
        # Determine which files to move (same logic as delete)
        if keep_strategy == "first":
            files_to_move = group[1:]
        elif keep_strategy == "last":
            files_to_move = group[:-1]
        else:
            files_to_move = group[1:]
        
        # Create move actions
        for i, file_path in enumerate(files_to_move):
            source = Path(file_path)
            # Create unique filename to avoid conflicts
            target_file = target_path / f"group_{group_id}_{i}_{source.name}"
            
            action_id = f"move_{group_id}_{len(actions)}"
            action = FileAction(
                action_id=action_id,
                action_type=ActionType.MOVE,
                source_path=file_path,
                target_path=str(target_file),
                metadata={"group_id": group_id, "keep_strategy": keep_strategy}
            )
            actions.append(action)
    
    return actions