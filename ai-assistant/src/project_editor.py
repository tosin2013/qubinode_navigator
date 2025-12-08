"""
Project Editor: Edit files in source projects with user approval.

This module provides:
- Propose edits to source project files
- Preview changes with diffs
- Apply edits with git tracking
- Rollback capability

Per ADR-0066: Developer Agent DAG Validation and Smart Pipelines
"""

import os
import logging
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class EditType(str, Enum):
    """Type of file edit."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class EditStatus(str, Enum):
    """Status of an edit."""

    PENDING = "pending"  # Awaiting approval
    APPROVED = "approved"  # Approved, ready to apply
    APPLIED = "applied"  # Successfully applied
    REJECTED = "rejected"  # User rejected
    FAILED = "failed"  # Application failed
    ROLLED_BACK = "rolled_back"  # Rolled back


@dataclass
class ProjectFileEdit:
    """A proposed edit to a source project file."""

    edit_id: str
    project_path: str  # e.g., "/opt/qubinode-pipelines"
    file_path: str  # Relative path within project
    edit_type: EditType
    current_content: Optional[str]  # For modify
    proposed_content: str
    reason: str  # Why this edit is needed
    status: EditStatus = EditStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None
    git_commit: Optional[str] = None
    backup_path: Optional[str] = None

    @property
    def absolute_path(self) -> str:
        """Get absolute path to the file."""
        return os.path.join(self.project_path, self.file_path)

    @property
    def diff(self) -> str:
        """Generate a unified diff of the changes."""
        if self.edit_type == EditType.CREATE:
            return f"+ {self.proposed_content}"
        elif self.edit_type == EditType.DELETE:
            return f"- {self.current_content}"
        else:
            return self._generate_diff(
                self.current_content or "",
                self.proposed_content,
            )

    def _generate_diff(self, old: str, new: str) -> str:
        """Generate a simple unified diff."""
        import difflib

        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{self.file_path}",
            tofile=f"b/{self.file_path}",
        )
        return "".join(diff)


@dataclass
class EditResult:
    """Result of applying an edit."""

    success: bool
    edit_id: str
    message: str
    git_commit: Optional[str] = None
    backup_path: Optional[str] = None
    rollback_available: bool = False


class ProjectEditor:
    """
    Manages file edits in source projects with approval workflow.

    Features:
    - Propose edits with previews
    - User approval before application
    - Git commit for tracking
    - Rollback capability
    """

    def __init__(self, backup_dir: str = "/tmp/qubinode_project_edits"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._pending_edits: Dict[str, ProjectFileEdit] = {}
        self._applied_edits: Dict[str, ProjectFileEdit] = {}

    def propose_edit(
        self,
        project_path: str,
        file_path: str,
        edit_type: EditType,
        proposed_content: str,
        reason: str,
    ) -> ProjectFileEdit:
        """
        Propose an edit to a project file.

        Returns the edit with a unique ID for approval/rejection.
        """
        # Generate edit ID
        edit_id = hashlib.md5(f"{project_path}:{file_path}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        # Read current content if modifying
        current_content = None
        if edit_type in (EditType.MODIFY, EditType.DELETE):
            abs_path = os.path.join(project_path, file_path)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r") as f:
                        current_content = f.read()
                except Exception as e:
                    logger.warning(f"Could not read file {abs_path}: {e}")

        edit = ProjectFileEdit(
            edit_id=edit_id,
            project_path=project_path,
            file_path=file_path,
            edit_type=edit_type,
            current_content=current_content,
            proposed_content=proposed_content,
            reason=reason,
        )

        self._pending_edits[edit_id] = edit
        logger.info(f"Proposed edit {edit_id}: {edit_type.value} {file_path}")

        return edit

    def get_pending_edit(self, edit_id: str) -> Optional[ProjectFileEdit]:
        """Get a pending edit by ID."""
        return self._pending_edits.get(edit_id)

    def get_all_pending_edits(self) -> List[ProjectFileEdit]:
        """Get all pending edits."""
        return list(self._pending_edits.values())

    def approve_edit(self, edit_id: str) -> Tuple[bool, str]:
        """
        Approve an edit for application.

        Returns (success, message).
        """
        edit = self._pending_edits.get(edit_id)
        if not edit:
            return False, f"Edit {edit_id} not found"

        if edit.status != EditStatus.PENDING:
            return False, f"Edit {edit_id} is not pending (status: {edit.status.value})"

        edit.status = EditStatus.APPROVED
        logger.info(f"Approved edit {edit_id}")
        return True, f"Edit {edit_id} approved"

    def reject_edit(self, edit_id: str, reason: str = "") -> Tuple[bool, str]:
        """
        Reject an edit.

        Returns (success, message).
        """
        edit = self._pending_edits.get(edit_id)
        if not edit:
            return False, f"Edit {edit_id} not found"

        if edit.status != EditStatus.PENDING:
            return False, f"Edit {edit_id} is not pending (status: {edit.status.value})"

        edit.status = EditStatus.REJECTED
        del self._pending_edits[edit_id]
        logger.info(f"Rejected edit {edit_id}: {reason}")
        return True, f"Edit {edit_id} rejected"

    def apply_edit(
        self,
        edit_id: str,
        commit_changes: bool = True,
    ) -> EditResult:
        """
        Apply an approved edit.

        Args:
            edit_id: The edit ID
            commit_changes: Whether to create a git commit

        Returns EditResult with status.
        """
        edit = self._pending_edits.get(edit_id)
        if not edit:
            return EditResult(
                success=False,
                edit_id=edit_id,
                message=f"Edit {edit_id} not found",
            )

        if edit.status != EditStatus.APPROVED:
            return EditResult(
                success=False,
                edit_id=edit_id,
                message=f"Edit {edit_id} is not approved (status: {edit.status.value})",
            )

        try:
            # Create backup
            backup_path = self._create_backup(edit)
            edit.backup_path = backup_path

            # Apply the edit
            if edit.edit_type == EditType.CREATE:
                self._create_file(edit)
            elif edit.edit_type == EditType.MODIFY:
                self._modify_file(edit)
            elif edit.edit_type == EditType.DELETE:
                self._delete_file(edit)

            # Commit if requested
            git_commit = None
            if commit_changes and self._is_git_repo(edit.project_path):
                git_commit = self._commit_changes(edit)
                edit.git_commit = git_commit

            # Update status
            edit.status = EditStatus.APPLIED
            edit.applied_at = datetime.now()

            # Move to applied edits
            del self._pending_edits[edit_id]
            self._applied_edits[edit_id] = edit

            logger.info(f"Applied edit {edit_id} to {edit.file_path}")

            return EditResult(
                success=True,
                edit_id=edit_id,
                message=f"Successfully applied edit to {edit.file_path}",
                git_commit=git_commit,
                backup_path=backup_path,
                rollback_available=True,
            )

        except Exception as e:
            edit.status = EditStatus.FAILED
            logger.error(f"Failed to apply edit {edit_id}: {e}")
            return EditResult(
                success=False,
                edit_id=edit_id,
                message=f"Failed to apply edit: {str(e)}",
            )

    def rollback_edit(self, edit_id: str) -> EditResult:
        """
        Rollback an applied edit using the backup.

        Returns EditResult with status.
        """
        edit = self._applied_edits.get(edit_id)
        if not edit:
            return EditResult(
                success=False,
                edit_id=edit_id,
                message=f"Applied edit {edit_id} not found",
            )

        if not edit.backup_path or not os.path.exists(edit.backup_path):
            return EditResult(
                success=False,
                edit_id=edit_id,
                message="Backup not available for rollback",
            )

        try:
            abs_path = edit.absolute_path

            if edit.edit_type == EditType.CREATE:
                # Delete the created file
                if os.path.exists(abs_path):
                    os.remove(abs_path)
            elif edit.edit_type == EditType.MODIFY:
                # Restore from backup
                with open(edit.backup_path, "r") as f:
                    original_content = f.read()
                with open(abs_path, "w") as f:
                    f.write(original_content)
            elif edit.edit_type == EditType.DELETE:
                # Restore deleted file from backup
                with open(edit.backup_path, "r") as f:
                    original_content = f.read()
                with open(abs_path, "w") as f:
                    f.write(original_content)

            edit.status = EditStatus.ROLLED_BACK
            logger.info(f"Rolled back edit {edit_id}")

            return EditResult(
                success=True,
                edit_id=edit_id,
                message=f"Successfully rolled back {edit.file_path}",
                rollback_available=False,
            )

        except Exception as e:
            logger.error(f"Failed to rollback edit {edit_id}: {e}")
            return EditResult(
                success=False,
                edit_id=edit_id,
                message=f"Failed to rollback: {str(e)}",
            )

    def _create_backup(self, edit: ProjectFileEdit) -> Optional[str]:
        """Create a backup of the original file."""
        abs_path = edit.absolute_path

        if not os.path.exists(abs_path):
            return None

        try:
            backup_path = self.backup_dir / f"{edit.edit_id}_backup"
            with open(abs_path, "r") as f:
                content = f.read()
            with open(backup_path, "w") as f:
                f.write(content)
            return str(backup_path)
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
            return None

    def _create_file(self, edit: ProjectFileEdit) -> None:
        """Create a new file."""
        abs_path = edit.absolute_path

        # Create parent directories
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w") as f:
            f.write(edit.proposed_content)

    def _modify_file(self, edit: ProjectFileEdit) -> None:
        """Modify an existing file."""
        abs_path = edit.absolute_path

        with open(abs_path, "w") as f:
            f.write(edit.proposed_content)

    def _delete_file(self, edit: ProjectFileEdit) -> None:
        """Delete a file."""
        abs_path = edit.absolute_path

        if os.path.exists(abs_path):
            os.remove(abs_path)

    def _is_git_repo(self, path: str) -> bool:
        """Check if path is in a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _commit_changes(self, edit: ProjectFileEdit) -> Optional[str]:
        """Create a git commit for the edit."""
        try:
            project_path = edit.project_path

            # Add the file
            subprocess.run(
                ["git", "add", edit.file_path],
                cwd=project_path,
                capture_output=True,
                timeout=10,
            )

            # Create commit
            commit_msg = f"[qubinode-ai] {edit.edit_type.value}: {edit.file_path}\n\n{edit.reason}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Get commit hash
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.stdout.strip()[:12]

            return None

        except Exception as e:
            logger.warning(f"Could not create git commit: {e}")
            return None

    def propose_profile_edit(
        self,
        project_name: str,
        profile_name: str,
        changes: Dict[str, Any],
    ) -> Optional[ProjectFileEdit]:
        """
        Propose an edit to a kcli profile.

        Convenience method for VM profile modifications.
        """
        # Import project registry to get project path
        try:
            from project_registry import get_project_registry
            import asyncio

            async def get_project():
                registry = await get_project_registry()
                return registry.get_project(project_name)

            project = asyncio.get_event_loop().run_until_complete(get_project())
            if not project:
                logger.warning(f"Project not found: {project_name}")
                return None

            project_path = project.path
            profile_path = f"kcli_profiles/{profile_name}.yml"
            abs_path = os.path.join(project_path, profile_path)

            # Read current profile
            current_content = ""
            if os.path.exists(abs_path):
                with open(abs_path, "r") as f:
                    current_content = f.read()

            # Parse and modify
            import yaml

            try:
                profile_data = yaml.safe_load(current_content) or {}
            except Exception:
                profile_data = {}

            # Apply changes
            for key, value in changes.items():
                profile_data[key] = value

            proposed_content = yaml.dump(profile_data, default_flow_style=False)

            # Build reason
            change_list = ", ".join(f"{k}={v}" for k, v in changes.items())
            reason = f"Update {profile_name} profile: {change_list}"

            return self.propose_edit(
                project_path=project_path,
                file_path=profile_path,
                edit_type=EditType.MODIFY if os.path.exists(abs_path) else EditType.CREATE,
                proposed_content=proposed_content,
                reason=reason,
            )

        except Exception as e:
            logger.error(f"Could not propose profile edit: {e}")
            return None


# Singleton instance
_editor: Optional[ProjectEditor] = None


def get_project_editor() -> ProjectEditor:
    """Get the singleton project editor instance."""
    global _editor
    if _editor is None:
        _editor = ProjectEditor()
    return _editor


def propose_file_edit(
    project_path: str,
    file_path: str,
    content: str,
    reason: str,
    edit_type: str = "modify",
) -> Dict[str, Any]:
    """
    Convenience function to propose a file edit.

    Returns dict with edit_id and preview.
    """
    editor = get_project_editor()

    type_map = {
        "create": EditType.CREATE,
        "modify": EditType.MODIFY,
        "delete": EditType.DELETE,
    }
    edit_type_enum = type_map.get(edit_type.lower(), EditType.MODIFY)

    edit = editor.propose_edit(
        project_path=project_path,
        file_path=file_path,
        edit_type=edit_type_enum,
        proposed_content=content,
        reason=reason,
    )

    return {
        "edit_id": edit.edit_id,
        "project_path": edit.project_path,
        "file_path": edit.file_path,
        "edit_type": edit.edit_type.value,
        "status": edit.status.value,
        "reason": edit.reason,
        "diff_preview": edit.diff[:2000],  # Limit diff size
        "user_actions": [
            {
                "action_type": "approve",
                "description": "Approve and apply this edit",
                "endpoint": "/orchestrator/projects/edits/approve",
            },
            {
                "action_type": "reject",
                "description": "Reject this edit",
                "endpoint": "/orchestrator/projects/edits/reject",
            },
            {
                "action_type": "modify",
                "description": "Request different changes",
            },
        ],
    }


def apply_approved_edit(edit_id: str, commit: bool = True) -> Dict[str, Any]:
    """
    Convenience function to apply an approved edit.

    Returns result dict.
    """
    editor = get_project_editor()

    # First approve if still pending
    edit = editor.get_pending_edit(edit_id)
    if edit and edit.status == EditStatus.PENDING:
        editor.approve_edit(edit_id)

    result = editor.apply_edit(edit_id, commit_changes=commit)

    return {
        "success": result.success,
        "edit_id": result.edit_id,
        "message": result.message,
        "git_commit": result.git_commit,
        "rollback_available": result.rollback_available,
    }
