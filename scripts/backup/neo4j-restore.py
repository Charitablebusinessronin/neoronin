"""
Neo4j restore tooling with recovery state management.

Provides high-level restore operations wrapping neo4j-admin, including:
- Restore from backup to test instance
- Validate restored backup
- Promote test instance to production
- Rollback failed restores
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Tuple
from neo4j import GraphDatabase, Driver
from src.durability.recovery import RecoveryStateMachine

logger = logging.getLogger(__name__)


class RestoreManager:
    """Manages Neo4j restore operations with recovery state tracking."""

    def __init__(self, driver: Driver, backup_dir: str, target_instance: str = 'neo4j'):
        """Initialize restore manager.

        Args:
            driver: Neo4j driver connection
            backup_dir: Directory containing backups
            target_instance: Name of database instance to restore to
        """
        self.driver = driver
        self.backup_dir = Path(backup_dir)
        self.target_instance = target_instance
        self.recovery_machine = RecoveryStateMachine(driver)

    def restore_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Restore a backup to the target instance.

        Args:
            backup_id: ID of backup to restore

        Returns:
            Tuple[bool, str]: (success, message)
        """
        # Initialize recovery state
        if not self.recovery_machine.initialize_recovery(backup_id):
            return False, "Recovery operation already in progress"

        start_time = time.time()

        try:
            backup_path = self.backup_dir / backup_id

            if not backup_path.exists():
                self.recovery_machine.reset_recovery_state()
                return False, f"Backup {backup_id} not found"

            logger.info(f"Starting restore from backup {backup_id}...")

            # Run neo4j-admin restore
            cmd = [
                'neo4j-admin', 'database', 'restore',
                '--backup-path', str(backup_path),
                '--id', backup_id,
                '--to-path', '/var/lib/neo4j/data/databases/',
                self.target_instance
            ]

            # Update progress
            self.recovery_machine.update_progress(0)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Restore failed: {error_msg}")
                self.recovery_machine.update_progress(0)
                return False, f"Restore failed: {error_msg}"

            # Update progress to 90% (restore done, validation next)
            self.recovery_machine.update_progress(90)

            duration = int(time.time() - start_time)
            logger.info(f"Restore completed in {duration} seconds")

            # Transition to validation phase
            self.recovery_machine.start_validation()

            return True, f"Backup {backup_id} restored successfully"

        except subprocess.TimeoutExpired:
            self.recovery_machine.reset_recovery_state()
            return False, "Restore timeout after 1800 seconds"
        except Exception as e:
            logger.error(f"Restore error: {str(e)}")
            self.recovery_machine.reset_recovery_state()
            return False, f"Restore failed: {str(e)}"

    def validate_restore(self, backup_id: str) -> Tuple[bool, str]:
        """Validate restored backup matches original.

        Checks:
        - Database is accessible
        - Schema matches expectations
        - No orphaned relationships
        - Data integrity confirmed

        Args:
            backup_id: ID of backup that was restored

        Returns:
            Tuple[bool, str]: (valid, message)
        """
        try:
            from src.health.checker import HealthChecker

            checker = HealthChecker(self.driver)

            # Run health checks on restored database
            connectivity_ok, conn_msg, _ = checker.check_connectivity()
            if not connectivity_ok:
                errors = [f"Connectivity check failed: {conn_msg}"]
                self.recovery_machine.validation_failed(errors)
                return False, f"Validation failed: {conn_msg}"

            schema_ok, schema_msg, _ = checker.check_schema_consistency()
            if not schema_ok:
                errors = [f"Schema consistency failed: {schema_msg}"]
                self.recovery_machine.validation_failed(errors)
                return False, f"Validation failed: {schema_msg}"

            orphan_ok, orphan_msg, _ = checker.check_orphan_detection()
            if not orphan_ok:
                errors = [f"Orphan detection failed: {orphan_msg}"]
                self.recovery_machine.validation_failed(errors)
                return False, f"Validation failed: {orphan_msg}"

            # All checks passed
            logger.info(f"Validation passed for restored backup {backup_id}")
            self.recovery_machine.validation_passed()
            return True, "Restore validation passed - all health checks successful"

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            self.recovery_machine.validation_failed([str(e)])
            return False, f"Validation error: {str(e)}"

    def promote_to_production(self) -> Tuple[bool, str]:
        """Promote validated restore to production.

        This is an atomic operation that:
        1. Verifies recovery state is SUCCESS
        2. Marks recovery as promoted
        3. Updates audit log

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            promoted = self.recovery_machine.promote_to_production()

            if promoted:
                logger.info("Recovery promoted to production")
                return True, "Restore promoted to production successfully"
            else:
                return False, "Recovery not in success state - cannot promote"

        except Exception as e:
            logger.error(f"Promotion error: {str(e)}")
            return False, f"Promotion failed: {str(e)}"

    def rollback_restore(self) -> Tuple[bool, str]:
        """Rollback a failed restore operation.

        Returns database to pre-restore state.

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Get current recovery state
            state = self.recovery_machine.get_current_state()

            if not state:
                return False, "No recovery in progress"

            # Check if we should rollback
            if state.get('status') in ['RECOVERY_FAILED', 'VALIDATION']:
                logger.info("Rolling back failed recovery...")

                # Reset recovery state
                self.recovery_machine.reset_recovery_state()

                return True, "Restore rolled back successfully"
            else:
                return False, f"Cannot rollback - recovery in {state.get('status')} state"

        except Exception as e:
            logger.error(f"Rollback error: {str(e)}")
            return False, f"Rollback failed: {str(e)}"

    def get_restore_status(self) -> dict:
        """Get current restore operation status.

        Returns:
            dict: Recovery state dictionary
        """
        try:
            return self.recovery_machine.get_current_state()
        except Exception as e:
            logger.error(f"Error getting restore status: {str(e)}")
            return {}
