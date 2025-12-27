"""
Durability orchestration interface for backup and restore operations.

High-level API for managing backup lifecycle and recovery operations,
integrating backup management, recovery state machine, and health checks.
"""

import logging
from typing import Dict, List, Tuple
from neo4j import Driver
from scripts.backup.neo4j_backup import BackupManager
from scripts.backup.neo4j_restore import RestoreManager
from src.health.checker import HealthChecker
from src.durability.recovery import RecoveryStateMachine

logger = logging.getLogger(__name__)


class DurabilityOrchestrator:
    """Orchestrates backup, restore, and recovery operations."""

    def __init__(self, driver: Driver, backup_dir: str):
        """Initialize durability orchestrator.

        Args:
            driver: Neo4j driver connection
            backup_dir: Directory for backup storage
        """
        self.driver = driver
        self.backup_manager = BackupManager(driver, backup_dir)
        self.restore_manager = RestoreManager(driver, backup_dir)
        self.health_checker = HealthChecker(driver)
        self.recovery_machine = RecoveryStateMachine(driver)

    def backup_and_verify(self, backup_id: str = None, compress: bool = True) -> Tuple[bool, str, Dict]:
        """Create a backup and immediately verify its integrity.

        Args:
            backup_id: Optional custom backup ID
            compress: Whether to compress backup

        Returns:
            Tuple[bool, str, Dict]: (success, message, metadata)
        """
        logger.info("Starting backup and verify operation...")

        # Create backup
        success, message, metadata = self.backup_manager.create_backup(
            backup_id=backup_id,
            compress=compress
        )

        if not success:
            return False, f"Backup failed: {message}", {}

        # Verify backup
        backup_id = metadata['id']
        is_valid, verify_msg = self.backup_manager.validate_backup(backup_id)

        if not is_valid:
            return False, f"Backup verification failed: {verify_msg}", metadata

        logger.info(f"Backup and verify succeeded: {backup_id}")
        return True, f"Backup created and verified: {backup_id}", metadata

    def restore_with_validation(self, backup_id: str) -> Tuple[bool, str]:
        """Restore a backup with full validation.

        Steps:
        1. Restore backup to test instance
        2. Run health checks on restored database
        3. If valid, mark recovery as success
        4. If invalid, mark recovery as failed and rollback

        Args:
            backup_id: ID of backup to restore

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info(f"Starting restore with validation: {backup_id}")

        # Check if another recovery is in progress
        state = self.recovery_machine.get_current_state()
        if state.get('status') in ['RECOVERING', 'VALIDATION']:
            return False, "Another recovery operation is already in progress"

        # Restore backup
        success, restore_msg = self.restore_manager.restore_backup(backup_id)

        if not success:
            logger.error(f"Restore failed: {restore_msg}")
            return False, f"Restore failed: {restore_msg}"

        logger.info("Restore completed, running validation checks...")

        # Validate restore
        is_valid, validation_msg = self.restore_manager.validate_restore(backup_id)

        if not is_valid:
            logger.error(f"Validation failed, rolling back: {validation_msg}")
            self.restore_manager.rollback_restore()
            return False, f"Validation failed: {validation_msg}"

        logger.info("Restore validation successful")
        return True, f"Restore and validation successful for {backup_id}"

    def promote_backup_to_production(self) -> Tuple[bool, str]:
        """Promote a validated backup to production.

        Prerequisites:
        - Restore must be in VALIDATION phase
        - All health checks must have passed

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info("Promoting backup to production...")

        # Get current recovery state
        state = self.recovery_machine.get_current_state()

        if not state:
            return False, "No recovery in progress"

        if state.get('status') != 'VALIDATION':
            return False, f"Cannot promote - recovery in {state.get('status')} state"

        # Run final health check before promotion
        health_result = self.health_checker.perform_all_checks(detailed=False)

        if health_result['status'] != 'healthy':
            logger.error(f"Pre-promotion health check failed")
            self.recovery_machine.validation_failed([
                f"Pre-promotion health check failed: {health_result.get('message', 'unknown error')}"
            ])
            return False, "Pre-promotion health check failed"

        # Promote to production
        success, promote_msg = self.restore_manager.promote_to_production()

        if success:
            logger.info("Successfully promoted to production")
            return True, promote_msg
        else:
            return False, f"Promotion failed: {promote_msg}"

    def check_database_health(self, detailed: bool = False) -> Dict:
        """Check current database health status.

        Args:
            detailed: Include detailed metrics

        Returns:
            Dict: Health check results
        """
        logger.info("Checking database health...")
        return self.health_checker.perform_all_checks(detailed=detailed)

    def list_backups_with_status(self) -> List[Dict]:
        """List all backups with current status.

        Returns:
            List[Dict]: List of backup metadata with status
        """
        logger.info("Listing backups...")
        backups = self.backup_manager.list_backups()

        # Enhance with current validation status
        for backup in backups:
            try:
                is_valid, msg = self.backup_manager.validate_backup(backup['id'])
                backup['validation_status'] = 'valid' if is_valid else 'invalid'
                backup['validation_message'] = msg
            except Exception as e:
                backup['validation_status'] = 'unknown'
                backup['validation_message'] = str(e)

        return backups

    def get_recovery_status(self) -> Dict:
        """Get current recovery operation status.

        Returns:
            Dict: Recovery state
        """
        logger.info("Getting recovery status...")
        return self.recovery_machine.get_current_state()

    def cleanup_old_backups(self, retention_days: int) -> Tuple[int, str]:
        """Delete backups older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Tuple[int, str]: (count_deleted, message)
        """
        logger.info(f"Cleaning up backups older than {retention_days} days...")
        return self.backup_manager.prune_old_backups(retention_days)

    def cancel_recovery_operation(self) -> Tuple[bool, str]:
        """Cancel an in-progress recovery operation.

        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info("Cancelling recovery operation...")

        try:
            state = self.recovery_machine.get_current_state()

            if not state or state.get('status') == 'NOT_RECOVERING':
                return False, "No recovery operation in progress"

            self.recovery_machine.reset_recovery_state()
            logger.info("Recovery operation cancelled")
            return True, "Recovery operation cancelled successfully"

        except Exception as e:
            logger.error(f"Error cancelling recovery: {str(e)}")
            return False, f"Error cancelling recovery: {str(e)}"
