"""
Tests for project_editor.py - File editing with approval workflow.

Tests cover:
- EditType and EditStatus enums
- ProjectFileEdit and EditResult dataclasses
- ProjectEditor class methods
- Singleton and convenience functions
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode
os.environ["TEST_MODE"] = "true"

from project_editor import (
    EditType,
    EditStatus,
    ProjectFileEdit,
    EditResult,
    ProjectEditor,
    get_project_editor,
    propose_file_edit,
    apply_approved_edit,
)


class TestEditType:
    """Tests for EditType enum."""

    def test_all_types_exist(self):
        """Test that all edit types are defined."""
        assert EditType.CREATE
        assert EditType.MODIFY
        assert EditType.DELETE

    def test_type_values(self):
        """Test edit type enum values."""
        assert EditType.CREATE.value == "create"
        assert EditType.MODIFY.value == "modify"
        assert EditType.DELETE.value == "delete"


class TestEditStatus:
    """Tests for EditStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all statuses are defined."""
        assert EditStatus.PENDING
        assert EditStatus.APPROVED
        assert EditStatus.APPLIED
        assert EditStatus.REJECTED
        assert EditStatus.FAILED
        assert EditStatus.ROLLED_BACK

    def test_status_values(self):
        """Test status enum values."""
        assert EditStatus.PENDING.value == "pending"
        assert EditStatus.APPROVED.value == "approved"
        assert EditStatus.APPLIED.value == "applied"


class TestProjectFileEdit:
    """Tests for ProjectFileEdit dataclass."""

    def test_edit_creation(self):
        """Test creating a file edit."""
        edit = ProjectFileEdit(
            edit_id="abc123",
            project_path="/opt/project",
            file_path="src/main.py",
            edit_type=EditType.CREATE,
            current_content=None,
            proposed_content="print('hello')",
            reason="Add main file",
        )
        assert edit.edit_id == "abc123"
        assert edit.project_path == "/opt/project"
        assert edit.file_path == "src/main.py"
        assert edit.status == EditStatus.PENDING
        assert edit.git_commit is None

    def test_absolute_path_property(self):
        """Test absolute_path property."""
        edit = ProjectFileEdit(
            edit_id="abc123",
            project_path="/opt/project",
            file_path="src/main.py",
            edit_type=EditType.CREATE,
            current_content=None,
            proposed_content="content",
            reason="Test",
        )
        assert edit.absolute_path == "/opt/project/src/main.py"

    def test_diff_for_create(self):
        """Test diff for create operation."""
        edit = ProjectFileEdit(
            edit_id="abc123",
            project_path="/opt/project",
            file_path="new.py",
            edit_type=EditType.CREATE,
            current_content=None,
            proposed_content="new content",
            reason="Create new file",
        )
        diff = edit.diff
        assert "new content" in diff

    def test_diff_for_delete(self):
        """Test diff for delete operation."""
        edit = ProjectFileEdit(
            edit_id="abc123",
            project_path="/opt/project",
            file_path="old.py",
            edit_type=EditType.DELETE,
            current_content="old content",
            proposed_content="",
            reason="Delete old file",
        )
        diff = edit.diff
        assert "old content" in diff

    def test_diff_for_modify(self):
        """Test diff for modify operation."""
        edit = ProjectFileEdit(
            edit_id="abc123",
            project_path="/opt/project",
            file_path="file.py",
            edit_type=EditType.MODIFY,
            current_content="line1\nline2\n",
            proposed_content="line1\nline2 modified\n",
            reason="Modify file",
        )
        diff = edit.diff
        assert "---" in diff or "line2" in diff


class TestEditResult:
    """Tests for EditResult dataclass."""

    def test_success_result(self):
        """Test successful edit result."""
        result = EditResult(
            success=True,
            edit_id="abc123",
            message="Applied successfully",
            git_commit="abcd1234",
            backup_path="/tmp/backup",
            rollback_available=True,
        )
        assert result.success is True
        assert result.git_commit == "abcd1234"
        assert result.rollback_available is True

    def test_failure_result(self):
        """Test failed edit result."""
        result = EditResult(
            success=False,
            edit_id="abc123",
            message="Failed to apply",
        )
        assert result.success is False
        assert result.git_commit is None
        assert result.rollback_available is False


class TestProjectEditor:
    """Tests for ProjectEditor class."""

    @pytest.fixture
    def editor(self):
        """Create a fresh editor for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ProjectEditor(backup_dir=tmpdir)

    @pytest.fixture
    def project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_editor_initialization(self, editor):
        """Test editor initializes correctly."""
        assert editor._pending_edits == {}
        assert editor._applied_edits == {}
        assert editor.backup_dir.exists()

    def test_propose_create_edit(self, editor, project_dir):
        """Test proposing a create edit."""
        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="new_file.py",
            edit_type=EditType.CREATE,
            proposed_content="print('hello')",
            reason="Add new file",
        )

        assert edit.edit_id is not None
        assert edit.edit_type == EditType.CREATE
        assert edit.status == EditStatus.PENDING
        assert edit.edit_id in editor._pending_edits

    def test_propose_modify_edit(self, editor, project_dir):
        """Test proposing a modify edit reads current content."""
        # Create existing file
        file_path = Path(project_dir) / "existing.py"
        file_path.write_text("original content")

        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="existing.py",
            edit_type=EditType.MODIFY,
            proposed_content="modified content",
            reason="Modify file",
        )

        assert edit.current_content == "original content"
        assert edit.proposed_content == "modified content"

    def test_get_pending_edit(self, editor, project_dir):
        """Test getting a pending edit."""
        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="test.py",
            edit_type=EditType.CREATE,
            proposed_content="content",
            reason="Test",
        )

        retrieved = editor.get_pending_edit(edit.edit_id)
        assert retrieved is not None
        assert retrieved.edit_id == edit.edit_id

    def test_get_pending_edit_not_found(self, editor):
        """Test getting a non-existent edit."""
        retrieved = editor.get_pending_edit("nonexistent")
        assert retrieved is None

    def test_get_all_pending_edits(self, editor, project_dir):
        """Test getting all pending edits."""
        editor.propose_edit(project_dir, "file1.py", EditType.CREATE, "c1", "r1")
        editor.propose_edit(project_dir, "file2.py", EditType.CREATE, "c2", "r2")

        pending = editor.get_all_pending_edits()
        assert len(pending) == 2

    def test_approve_edit(self, editor, project_dir):
        """Test approving an edit."""
        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="test.py",
            edit_type=EditType.CREATE,
            proposed_content="content",
            reason="Test",
        )

        success, msg = editor.approve_edit(edit.edit_id)

        assert success is True
        assert edit.status == EditStatus.APPROVED

    def test_approve_edit_not_found(self, editor):
        """Test approving a non-existent edit."""
        success, msg = editor.approve_edit("nonexistent")
        assert success is False
        assert "not found" in msg.lower()

    def test_approve_edit_not_pending(self, editor, project_dir):
        """Test approving an already approved edit."""
        edit = editor.propose_edit(project_dir, "test.py", EditType.CREATE, "c", "r")
        editor.approve_edit(edit.edit_id)

        success, msg = editor.approve_edit(edit.edit_id)
        assert success is False
        assert "not pending" in msg.lower()

    def test_reject_edit(self, editor, project_dir):
        """Test rejecting an edit."""
        edit = editor.propose_edit(project_dir, "test.py", EditType.CREATE, "c", "r")

        success, msg = editor.reject_edit(edit.edit_id, "Not needed")

        assert success is True
        assert edit.edit_id not in editor._pending_edits

    def test_reject_edit_not_found(self, editor):
        """Test rejecting a non-existent edit."""
        success, msg = editor.reject_edit("nonexistent")
        assert success is False

    def test_apply_create_edit(self, editor, project_dir):
        """Test applying a create edit."""
        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="new_file.py",
            edit_type=EditType.CREATE,
            proposed_content="print('hello')",
            reason="Add file",
        )
        editor.approve_edit(edit.edit_id)

        result = editor.apply_edit(edit.edit_id, commit_changes=False)

        assert result.success is True
        assert (Path(project_dir) / "new_file.py").exists()
        assert edit.status == EditStatus.APPLIED

    def test_apply_modify_edit(self, editor, project_dir):
        """Test applying a modify edit."""
        # Create existing file
        file_path = Path(project_dir) / "existing.py"
        file_path.write_text("original")

        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="existing.py",
            edit_type=EditType.MODIFY,
            proposed_content="modified",
            reason="Modify",
        )
        editor.approve_edit(edit.edit_id)

        result = editor.apply_edit(edit.edit_id, commit_changes=False)

        assert result.success is True
        assert file_path.read_text() == "modified"

    def test_apply_delete_edit(self, editor, project_dir):
        """Test applying a delete edit."""
        # Create file to delete
        file_path = Path(project_dir) / "to_delete.py"
        file_path.write_text("delete me")

        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="to_delete.py",
            edit_type=EditType.DELETE,
            proposed_content="",
            reason="Delete file",
        )
        editor.approve_edit(edit.edit_id)

        result = editor.apply_edit(edit.edit_id, commit_changes=False)

        assert result.success is True
        assert not file_path.exists()

    def test_apply_edit_not_found(self, editor):
        """Test applying a non-existent edit."""
        result = editor.apply_edit("nonexistent")
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_apply_edit_not_approved(self, editor, project_dir):
        """Test applying a non-approved edit."""
        edit = editor.propose_edit(project_dir, "test.py", EditType.CREATE, "c", "r")

        result = editor.apply_edit(edit.edit_id)

        assert result.success is False
        assert "not approved" in result.message.lower()

    def test_rollback_modify_edit(self, editor, project_dir):
        """Test rolling back a modify edit."""
        # Create and modify a file
        file_path = Path(project_dir) / "rollback_test.py"
        file_path.write_text("original content")

        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="rollback_test.py",
            edit_type=EditType.MODIFY,
            proposed_content="modified content",
            reason="Test modify",
        )
        editor.approve_edit(edit.edit_id)
        editor.apply_edit(edit.edit_id, commit_changes=False)

        # Now rollback
        result = editor.rollback_edit(edit.edit_id)

        assert result.success is True
        assert file_path.read_text() == "original content"

    def test_rollback_create_edit_no_backup(self, editor, project_dir):
        """Test that rollback fails for create edits (no backup available)."""
        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="created_file.py",
            edit_type=EditType.CREATE,
            proposed_content="new content",
            reason="Create file",
        )
        editor.approve_edit(edit.edit_id)
        editor.apply_edit(edit.edit_id, commit_changes=False)

        file_path = Path(project_dir) / "created_file.py"
        assert file_path.exists()

        # Rollback fails for CREATE since there's no backup (file didn't exist before)
        result = editor.rollback_edit(edit.edit_id)

        # The current implementation requires backup for rollback
        assert result.success is False
        assert "backup" in result.message.lower()

    def test_rollback_delete_edit(self, editor, project_dir):
        """Test rolling back a delete edit."""
        # Create file and delete it
        file_path = Path(project_dir) / "deleted_file.py"
        file_path.write_text("original content")

        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="deleted_file.py",
            edit_type=EditType.DELETE,
            proposed_content="",
            reason="Delete file",
        )
        editor.approve_edit(edit.edit_id)
        editor.apply_edit(edit.edit_id, commit_changes=False)

        assert not file_path.exists()

        # Rollback should restore the file
        result = editor.rollback_edit(edit.edit_id)

        assert result.success is True
        assert file_path.exists()
        assert file_path.read_text() == "original content"

    def test_rollback_not_found(self, editor):
        """Test rolling back a non-existent edit."""
        result = editor.rollback_edit("nonexistent")
        assert result.success is False

    def test_is_git_repo_true(self, editor):
        """Test _is_git_repo returns True for git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            import subprocess

            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)

            result = editor._is_git_repo(tmpdir)
            assert result is True

    def test_is_git_repo_false(self, editor):
        """Test _is_git_repo returns False for non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = editor._is_git_repo(tmpdir)
            assert result is False

    def test_apply_edit_creates_parent_dirs(self, editor, project_dir):
        """Test that apply_edit creates parent directories."""
        edit = editor.propose_edit(
            project_path=project_dir,
            file_path="nested/deep/file.py",
            edit_type=EditType.CREATE,
            proposed_content="content",
            reason="Create nested file",
        )
        editor.approve_edit(edit.edit_id)

        result = editor.apply_edit(edit.edit_id, commit_changes=False)

        assert result.success is True
        assert (Path(project_dir) / "nested" / "deep" / "file.py").exists()


class TestSingletonAndConvenience:
    """Tests for singleton and convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton before each test."""
        import project_editor

        project_editor._editor = None
        yield
        project_editor._editor = None

    def test_get_project_editor(self):
        """Test get_project_editor returns an editor."""
        editor = get_project_editor()
        assert editor is not None
        assert isinstance(editor, ProjectEditor)

    def test_get_project_editor_singleton(self):
        """Test get_project_editor returns same instance."""
        editor1 = get_project_editor()
        editor2 = get_project_editor()
        assert editor1 is editor2

    def test_propose_file_edit_function(self):
        """Test propose_file_edit convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = propose_file_edit(
                project_path=tmpdir,
                file_path="test.py",
                content="print('hello')",
                reason="Add test file",
                edit_type="create",
            )

            assert "edit_id" in result
            assert result["edit_type"] == "create"
            assert result["status"] == "pending"
            assert "user_actions" in result

    def test_propose_file_edit_modify(self):
        """Test propose_file_edit for modify."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing file
            (Path(tmpdir) / "existing.py").write_text("original")

            result = propose_file_edit(
                project_path=tmpdir,
                file_path="existing.py",
                content="modified",
                reason="Modify file",
                edit_type="modify",
            )

            assert result["edit_type"] == "modify"

    def test_apply_approved_edit_function(self):
        """Test apply_approved_edit convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First propose an edit
            propose_result = propose_file_edit(
                project_path=tmpdir,
                file_path="test.py",
                content="print('hello')",
                reason="Add file",
                edit_type="create",
            )

            # Then apply it
            apply_result = apply_approved_edit(
                propose_result["edit_id"],
                commit=False,
            )

            assert apply_result["success"] is True
            assert (Path(tmpdir) / "test.py").exists()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def editor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ProjectEditor(backup_dir=tmpdir)

    def test_propose_modify_nonexistent_file(self, editor):
        """Test proposing modify for non-existent file."""
        with tempfile.TemporaryDirectory() as project_dir:
            edit = editor.propose_edit(
                project_path=project_dir,
                file_path="nonexistent.py",
                edit_type=EditType.MODIFY,
                proposed_content="new content",
                reason="Modify non-existent",
            )

            # Should still create the edit, but current_content is None
            assert edit.current_content is None

    def test_backup_created_for_existing_file(self, editor):
        """Test that backup is created for existing files."""
        with tempfile.TemporaryDirectory() as project_dir:
            file_path = Path(project_dir) / "backup_test.py"
            file_path.write_text("original content")

            edit = editor.propose_edit(
                project_path=project_dir,
                file_path="backup_test.py",
                edit_type=EditType.MODIFY,
                proposed_content="new content",
                reason="Test backup",
            )
            editor.approve_edit(edit.edit_id)
            result = editor.apply_edit(edit.edit_id, commit_changes=False)

            assert result.backup_path is not None
            assert Path(result.backup_path).exists()

    def test_diff_with_empty_current_content(self):
        """Test diff generation when current content is None."""
        edit = ProjectFileEdit(
            edit_id="abc123",
            project_path="/opt/project",
            file_path="file.py",
            edit_type=EditType.MODIFY,
            current_content=None,
            proposed_content="new content",
            reason="Test",
        )
        # Should not raise an error
        diff = edit.diff
        assert "new content" in diff
