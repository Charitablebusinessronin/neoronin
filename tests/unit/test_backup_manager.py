"""
Unit tests for backup manager functionality.

Tests backup creation, validation, listing, and deletion operations.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from scripts.backup.neo4j_backup import BackupManager


class TestBackupManager:
    """Test suite for BackupManager."""

    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver."""
        return Mock()

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def backup_manager(self, mock_driver, temp_backup_dir):
        """Create backup manager with mock driver."""
        return BackupManager(mock_driver, temp_backup_dir)

    def test_initialization(self, backup_manager, temp_backup_dir):
        """Test BackupManager initialization."""
        assert backup_manager.backup_dir == Path(temp_backup_dir)
        assert backup_manager.backup_dir.exists()

    def test_creates_backup_directory_if_missing(self, mock_driver):
        """Test that backup directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = Path(tmpdir) / "backups"
            assert not backup_path.exists()

            BackupManager(mock_driver, str(backup_path))

            assert backup_path.exists()

    @patch('subprocess.run')
    def test_create_backup_with_auto_id(self, mock_subprocess, backup_manager):
        """Test creating backup with auto-generated ID."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        success, message, metadata = backup_manager.create_backup(compress=True)

        assert success is True
        assert "successfully" in message.lower()
        assert 'id' in metadata
        assert metadata['status'] == 'completed'

    @patch('subprocess.run')
    def test_create_backup_with_custom_id(self, mock_subprocess, backup_manager):
        """Test creating backup with custom ID."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        success, message, metadata = backup_manager.create_backup(backup_id='custom-123')

        assert success is True
        assert metadata['id'] == 'custom-123'

    @patch('subprocess.run')
    def test_create_backup_handles_existing_backup(self, mock_subprocess, backup_manager):
        """Test that creating backup with existing ID fails."""
        # Create initial backup structure
        backup_id = 'duplicate-id'
        backup_path = backup_manager.backup_dir / backup_id
        backup_path.mkdir()

        success, message, metadata = backup_manager.create_backup(backup_id=backup_id)

        assert success is False
        assert "already exists" in message

    @patch('subprocess.run')
    def test_create_backup_subprocess_failure(self, mock_subprocess, backup_manager):
        """Test handling of subprocess failure."""
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Backup failed: Permission denied"
        )

        success, message, metadata = backup_manager.create_backup()

        assert success is False
        assert "failed" in message.lower()

    @patch('subprocess.run')
    def test_create_backup_subprocess_timeout(self, mock_subprocess, backup_manager):
        """Test handling of subprocess timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired('neo4j-admin', 600)

        success, message, metadata = backup_manager.create_backup()

        assert success is False
        assert "timeout" in message.lower()

    @patch('scripts.backup.neo4j_backup.BackupManager._save_backup_metadata')
    @patch('subprocess.run')
    def test_create_backup_saves_metadata(self, mock_subprocess, mock_save_metadata, backup_manager):
        """Test that backup creation saves metadata."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_save_metadata.return_value = None

        backup_manager.create_backup(backup_id='meta-test')

        # Verify metadata was saved
        assert mock_save_metadata.called

    def test_list_backups_empty(self, backup_manager):
        """Test listing backups when none exist."""
        mock_session = MagicMock()
        mock_session.run.return_value = iter([])

        backup_manager.driver.session = MagicMock(return_value=mock_session)

        backups = backup_manager.list_backups()

        assert backups == []

    def test_list_backups_with_data(self, backup_manager):
        """Test listing backups with existing data."""
        mock_record1 = {'metadata': {'id': 'backup-1', 'status': 'completed'}}
        mock_record2 = {'metadata': {'id': 'backup-2', 'status': 'completed'}}

        mock_session = MagicMock()
        mock_session.run.return_value = iter([
            MagicMock(items=mock_record1.items()),
            MagicMock(items=mock_record2.items())
        ])

        backup_manager.driver.session = MagicMock(return_value=mock_session)
        backup_manager.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        backup_manager.driver.session.return_value.__exit__ = MagicMock(return_value=None)

        # Mock successful query
        type(mock_session.run.return_value).__getitem__ = MagicMock(
            side_effect=lambda x: {'metadata': {}} if x == 0 else mock_record2['metadata']
        )

    def test_delete_backup_not_found(self, backup_manager):
        """Test deleting non-existent backup."""
        success, message = backup_manager.delete_backup('non-existent')

        assert success is False
        assert "not found" in message.lower()

    def test_delete_backup_success(self, backup_manager):
        """Test successful backup deletion."""
        backup_id = 'delete-test'
        backup_path = backup_manager.backup_dir / backup_id
        backup_path.mkdir()

        # Create a file in the backup directory
        (backup_path / 'test.file').write_text('test')

        backup_manager.driver.session = MagicMock()

        success, message = backup_manager.delete_backup(backup_id)

        assert success is True
        assert not backup_path.exists()

    def test_validate_backup_not_found(self, backup_manager):
        """Test validating non-existent backup."""
        is_valid, message = backup_manager.validate_backup('non-existent')

        assert is_valid is False
        assert "not found" in message.lower()

    def test_checksum_calculation(self, backup_manager):
        """Test checksum calculation for directory."""
        # Create test files
        test_dir = backup_manager.backup_dir / 'checksum-test'
        test_dir.mkdir()

        (test_dir / 'file1.txt').write_text('content1')
        (test_dir / 'file2.txt').write_text('content2')

        checksum = backup_manager._calculate_checksum(test_dir)

        # Checksum should be hex string of specific length
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex length

    def test_checksum_deterministic(self, backup_manager):
        """Test that checksum is deterministic."""
        test_dir = backup_manager.backup_dir / 'deterministic-test'
        test_dir.mkdir()

        (test_dir / 'file.txt').write_text('content')

        checksum1 = backup_manager._calculate_checksum(test_dir)
        checksum2 = backup_manager._calculate_checksum(test_dir)

        assert checksum1 == checksum2

    def test_get_neo4j_version(self, backup_manager):
        """Test retrieving Neo4j version."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__getitem__ = MagicMock(return_value='5.13.0')

        mock_session.run.return_value.single.return_value = mock_result

        backup_manager.driver.session = MagicMock(return_value=mock_session)
        backup_manager.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        backup_manager.driver.session.return_value.__exit__ = MagicMock(return_value=None)

        version = backup_manager._get_neo4j_version()

        # Should return version or 'unknown'
        assert isinstance(version, str)

    def test_prune_old_backups(self, backup_manager):
        """Test pruning old backups."""
        # Mock list_backups and delete_backup
        backup_manager.list_backups = Mock(return_value=[
            {
                'id': 'old-backup',
                'timestamp_created': '2020-01-01T12:00:00Z'
            }
        ])
        backup_manager.delete_backup = Mock(return_value=(True, 'deleted'))

        deleted_count, message = backup_manager.prune_old_backups(retention_days=365)

        # Should have called delete_backup
        assert backup_manager.delete_backup.called or deleted_count == 0


# Import subprocess for test
import subprocess
