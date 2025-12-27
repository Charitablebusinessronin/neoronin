"""
Recovery State Machine for Neo4j durability operations.

Manages the state transitions during database backup/restore operations,
tracking progress and validation status.
"""

import logging
from enum import Enum
from typing import Optional
from datetime import datetime
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """Recovery operation status states."""
    NOT_RECOVERING = "NOT_RECOVERING"
    RECOVERING = "RECOVERING"
    VALIDATION = "VALIDATION"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    RECOVERY_SUCCESS = "RECOVERY_SUCCESS"


class RecoveryStateMachine:
    """Manages recovery state and transitions in Neo4j."""

    def __init__(self, driver: Driver):
        """Initialize recovery state machine.

        Args:
            driver: Neo4j driver connection
        """
        self.driver = driver

    def get_current_state(self) -> dict:
        """Get current recovery state from database.

        Returns:
            dict: Current recovery state or empty dict if none exists
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                RETURN r {.*, status: r.status} as state
                """
            )
            record = result.single()
            if record:
                return dict(record['state'])
            return {}

    def initialize_recovery(self, backup_id: str) -> bool:
        """Start a new recovery operation.

        Args:
            backup_id: ID of the backup to restore

        Returns:
            bool: True if recovery initialized, False if one is already in progress
        """
        with self.driver.session() as session:
            # Check if recovery already in progress
            current = session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                WHERE r.status IN ['RECOVERING', 'VALIDATION']
                RETURN r
                """
            ).single()

            if current:
                logger.warning("Recovery already in progress")
                return False

            # Create or update recovery state
            timestamp = datetime.utcnow().isoformat() + "Z"
            session.run(
                """
                MERGE (r:RecoveryState {id: 'recovery-current'})
                SET r.status = $status,
                    r.backup_id = $backup_id,
                    r.started_at = $started_at,
                    r.progress_percent = 0,
                    r.target_instance = 'test-neo4j'
                RETURN r
                """,
                status=RecoveryStatus.RECOVERING.value,
                backup_id=backup_id,
                started_at=timestamp
            )

            logger.info(f"Recovery initialized for backup {backup_id}")
            return True

    def update_progress(self, progress_percent: int) -> None:
        """Update recovery progress.

        Args:
            progress_percent: Progress percentage (0-100)
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                WHERE r.status = $status
                SET r.progress_percent = $progress
                RETURN r
                """,
                status=RecoveryStatus.RECOVERING.value,
                progress=min(100, max(0, progress_percent))
            )
            logger.debug(f"Recovery progress: {progress_percent}%")

    def start_validation(self) -> None:
        """Transition to validation phase after restore completes."""
        with self.driver.session() as session:
            timestamp = datetime.utcnow().isoformat() + "Z"
            session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                WHERE r.status = $old_status
                SET r.status = $new_status,
                    r.progress_percent = 100
                RETURN r
                """,
                old_status=RecoveryStatus.RECOVERING.value,
                new_status=RecoveryStatus.VALIDATION.value
            )
            logger.info("Recovery: entering validation phase")

    def validation_passed(self) -> None:
        """Mark recovery as successful after validation passes."""
        with self.driver.session() as session:
            timestamp = datetime.utcnow().isoformat() + "Z"
            session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                WHERE r.status = $validation_status
                SET r.status = $success_status,
                    r.completed_at = $completed_at
                RETURN r
                """,
                validation_status=RecoveryStatus.VALIDATION.value,
                success_status=RecoveryStatus.RECOVERY_SUCCESS.value,
                completed_at=timestamp
            )
            logger.info("Recovery validation passed - recovery successful")

    def validation_failed(self, errors: list) -> None:
        """Mark recovery as failed after validation fails.

        Args:
            errors: List of validation error messages
        """
        with self.driver.session() as session:
            timestamp = datetime.utcnow().isoformat() + "Z"
            session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                WHERE r.status = $validation_status
                SET r.status = $failed_status,
                    r.completed_at = $completed_at,
                    r.validation_errors = $errors
                RETURN r
                """,
                validation_status=RecoveryStatus.VALIDATION.value,
                failed_status=RecoveryStatus.RECOVERY_FAILED.value,
                completed_at=timestamp,
                errors=errors
            )
            logger.error(f"Recovery validation failed: {errors}")

    def promote_to_production(self) -> bool:
        """Mark recovery as promoted to production.

        Returns:
            bool: True if promoted, False if not in success state
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (r:RecoveryState {id: 'recovery-current'})
                WHERE r.status = $success_status
                SET r.promoted_to_production = true,
                    r.promoted_at = $promoted_at
                RETURN r
                """,
                success_status=RecoveryStatus.RECOVERY_SUCCESS.value,
                promoted_at=datetime.utcnow().isoformat() + "Z"
            )

            if result.single():
                logger.info("Recovery promoted to production")
                return True
            return False

    def reset_recovery_state(self) -> None:
        """Reset recovery state to NOT_RECOVERING."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (r:RecoveryState {id: 'recovery-current'})
                SET r.status = $status,
                    r.backup_id = null,
                    r.started_at = null,
                    r.progress_percent = 0,
                    r.validation_errors = null
                RETURN r
                """,
                status=RecoveryStatus.NOT_RECOVERING.value
            )
            logger.info("Recovery state reset to NOT_RECOVERING")
