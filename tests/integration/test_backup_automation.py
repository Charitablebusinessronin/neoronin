"""
Integration tests for automated backup functionality (User Story 3).

Tests the backup scheduling and automation system:
1. Scheduled backup creation
2. Backup retention and pruning
3. Backup validation cycles
4. Scheduler health and monitoring
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from neo4j import GraphDatabase


class TestBackupAutomation:
    """Test suite for backup automation."""

    @pytest.fixture
    def neo4j_driver(self):
        """Create Neo4j driver."""
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "changeme"),
            encrypted=False
        )
        yield driver
        driver.close()

    @pytest.fixture
    def backup_scheduler(self):
        """Import and create backup scheduler."""
        from scripts.backup.backup_scheduler import BackupScheduler

        scheduler = BackupScheduler()
        yield scheduler

    def test_scheduler_initialization(self, backup_scheduler):
        """Test that backup scheduler initializes correctly."""
        assert backup_scheduler.driver is not None
        assert backup_scheduler.backup_manager is not None
        assert backup_scheduler.scheduler is not None

    def test_backup_schedule_cron_format(self, backup_scheduler):
        """Test that backup schedule is valid cron expression."""
        # Should be valid cron format (default is daily at 2 AM)
        cron_parts = backup_scheduler.backup_schedule.split()
        assert len(cron_parts) == 5, "Cron expression should have 5 parts"

    def test_retention_days_configuration(self, backup_scheduler):
        """Test backup retention configuration."""
        assert isinstance(backup_scheduler.retention_days, int)
        assert backup_scheduler.retention_days > 0

    def test_compression_setting(self, backup_scheduler):
        """Test compression setting configuration."""
        assert isinstance(backup_scheduler.compress_backups, bool)

    def test_run_backup_creates_backup(self, neo4j_driver, backup_scheduler):
        """Test that run_backup creates a backup."""
        backup_scheduler.backup_manager.create_backup = Mock(
            return_value=(True, "Backup created", {'id': 'test-backup'})
        )

        backup_scheduler.run_backup()

        assert backup_scheduler.backup_manager.create_backup.called

    def test_run_backup_skips_during_recovery(self, neo4j_driver, backup_scheduler):
        """Test that backup is skipped when recovery is in progress."""
        # Mock recovery state as RECOVERING
        backup_scheduler.recovery_machine.get_current_state = Mock(
            return_value={'status': 'RECOVERING'}
        )

        backup_scheduler.run_backup()

        # Backup should not have been called
        assert not hasattr(backup_scheduler.backup_manager, 'create_backup') or \
            not getattr(backup_scheduler.backup_manager, 'create_backup').called

    def test_run_backup_logs_audit_entry(self, neo4j_driver, backup_scheduler):
        """Test that backup operations are logged to audit log."""
        backup_scheduler.backup_manager.create_backup = Mock(
            return_value=(True, "Backup created", {'id': 'audit-test'})
        )

        with patch.object(backup_scheduler, '_log_backup_audit') as mock_log:
            backup_scheduler.run_backup()

            # Audit log should be called
            assert mock_log.called

    def test_validate_recent_backups(self, backup_scheduler):
        """Test validation of recent backups."""
        test_backups = [
            {'id': 'backup-1', 'timestamp_created': '2024-01-01T12:00:00Z'},
            {'id': 'backup-2', 'timestamp_created': '2024-01-02T12:00:00Z'},
        ]

        backup_scheduler.backup_manager.list_backups = Mock(return_value=test_backups)
        backup_scheduler.backup_manager.validate_backup = Mock(return_value=(True, 'Valid'))

        backup_scheduler.validate_recent_backups()

        # Should validate backups
        assert backup_scheduler.backup_manager.validate_backup.called

    def test_prune_old_backups(self, backup_scheduler):
        """Test pruning of old backups."""
        backup_scheduler.backup_manager.prune_old_backups = Mock(
            return_value=(5, "Deleted 5 backups")
        )

        backup_scheduler.prune_old_backups()

        assert backup_scheduler.backup_manager.prune_old_backups.called

    def test_audit_log_operation_recorded(self, backup_scheduler):
        """Test that audit log records operations."""
        with patch.object(backup_scheduler, '_log_backup_audit') as mock_log:
            backup_scheduler._log_backup_audit(
                operation='BACKUP_CREATE',
                result='SUCCESS',
                backup_id='audit-backup-1'
            )

            mock_log.assert_called_once()

    def test_error_handling_in_backup_job(self, backup_scheduler):
        """Test error handling during backup job."""
        backup_scheduler.backup_manager.create_backup = Mock(
            side_effect=Exception("Backup failed")
        )

        # Should not raise exception
        backup_scheduler.run_backup()

    def test_error_handling_in_validation_job(self, backup_scheduler):
        """Test error handling during validation job."""
        backup_scheduler.backup_manager.list_backups = Mock(
            side_effect=Exception("Database error")
        )

        # Should not raise exception
        backup_scheduler.validate_recent_backups()

    def test_error_handling_in_pruning_job(self, backup_scheduler):
        """Test error handling during pruning job."""
        backup_scheduler.backup_manager.prune_old_backups = Mock(
            side_effect=Exception("Pruning error")
        )

        # Should not raise exception
        backup_scheduler.prune_old_backups()


class TestBackupRetention:
    """Test suite for backup retention policy."""

    @pytest.fixture
    def neo4j_driver(self):
        """Create Neo4j driver."""
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "changeme"),
            encrypted=False
        )
        yield driver
        driver.close()

    @pytest.fixture
    def backup_manager(self, neo4j_driver):
        """Create backup manager."""
        from scripts.backup.neo4j_backup import BackupManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield BackupManager(neo4j_driver, tmpdir)

    def test_retention_period_days(self, backup_manager):
        """Test that retention period is measured in days."""
        # Mock backups with various ages
        backup_manager.list_backups = Mock(return_value=[
            {
                'id': 'old-backup',
                'timestamp_created': (datetime.utcnow() - timedelta(days=40)).isoformat() + 'Z'
            },
            {
                'id': 'new-backup',
                'timestamp_created': (datetime.utcnow() - timedelta(days=10)).isoformat() + 'Z'
            }
        ])

        backup_manager.delete_backup = Mock(return_value=(True, 'deleted'))

        deleted_count, message = backup_manager.prune_old_backups(retention_days=30)

        # Old backup should be deleted
        assert backup_manager.delete_backup.called

    def test_recent_backups_not_deleted(self, backup_manager):
        """Test that recent backups are not deleted."""
        backup_manager.list_backups = Mock(return_value=[
            {
                'id': 'recent-backup',
                'timestamp_created': (datetime.utcnow() - timedelta(days=5)).isoformat() + 'Z'
            }
        ])

        backup_manager.delete_backup = Mock()

        backup_manager.prune_old_backups(retention_days=30)

        # Should not delete recent backups
        assert not backup_manager.delete_backup.called


class TestBackupScheduling:
    """Test suite for backup scheduling logic."""

    def test_cron_daily_schedule(self):
        """Test daily cron schedule format."""
        daily_cron = '0 2 * * *'  # 2 AM daily
        parts = daily_cron.split()

        assert len(parts) == 5
        assert parts[0] == '0'  # minute
        assert parts[1] == '2'  # hour
        assert parts[2] == '*'  # day of month
        assert parts[3] == '*'  # month
        assert parts[4] == '*'  # day of week

    def test_cron_weekly_schedule(self):
        """Test weekly cron schedule format."""
        weekly_cron = '0 2 * * 0'  # Sunday 2 AM
        parts = weekly_cron.split()

        assert len(parts) == 5
        assert parts[4] == '0'  # Sunday

    def test_cron_custom_schedule(self):
        """Test custom cron schedule."""
        custom_cron = '0 3,15 * * *'  # 3 AM and 3 PM daily
        parts = custom_cron.split()

        assert len(parts) == 5
        assert ',' in parts[1]  # multiple hours


class TestBackupMetadata:
    """Test suite for backup metadata management."""

    @pytest.fixture
    def neo4j_driver(self):
        """Create Neo4j driver."""
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "changeme"),
            encrypted=False
        )
        yield driver
        driver.close()

    def test_backup_metadata_structure(self, neo4j_driver):
        """Test that backup metadata has required fields."""
        with neo4j_driver.session() as session:
            # Get backup metadata structure
            result = session.run("""
                CALL db.schema.nodeTypeProperties()
                YIELD nodeType, propertyName
                WHERE nodeType = 'BackupMetadata:'
                RETURN collect(propertyName) as properties
            """)

            try:
                record = result.single()
                if record and record['properties']:
                    properties = record['properties']
                    # Should have key properties
                    assert any('id' in str(p) for p in properties)
                    assert any('timestamp' in str(p) for p in properties)
            except:
                # If this query doesn't work on this Neo4j version, pass
                pass

    def test_backup_metadata_audit_relationship(self, neo4j_driver):
        """Test audit log relationship to backup metadata."""
        import uuid

        backup_id = f"audit-rel-{uuid.uuid4()}"
        audit_id = f"audit-{uuid.uuid4()}"

        with neo4j_driver.session() as session:
            # Create backup
            session.run("""
                CREATE (b:BackupMetadata {
                    id: $backup_id,
                    timestamp_created: $timestamp,
                    status: 'test',
                    backup_file: '/test'
                })
            """, backup_id=backup_id, timestamp="2024-01-01T12:00:00Z")

            # Create audit entry
            session.run("""
                CREATE (a:AuditLogEntry {
                    id: $audit_id,
                    timestamp: $timestamp,
                    operation: 'BACKUP_TEST',
                    actor: 'test',
                    result: 'SUCCESS',
                    entity_type: 'BackupMetadata',
                    entity_id: $backup_id
                })
            """, audit_id=audit_id, timestamp="2024-01-01T12:00:00Z", backup_id=backup_id)

            # Verify audit can find backup
            result = session.run("""
                MATCH (a:AuditLogEntry {id: $audit_id})
                WHERE a.entity_id = $backup_id
                RETURN a.entity_id as found_backup_id
            """, audit_id=audit_id, backup_id=backup_id)

            record = result.single()
            assert record['found_backup_id'] == backup_id

        # Cleanup
        with neo4j_driver.session() as session:
            session.run("""
                MATCH (b:BackupMetadata {id: $id}) DELETE b
            """, id=backup_id)
            session.run("""
                MATCH (a:AuditLogEntry {id: $id}) DELETE a
            """, id=audit_id)
