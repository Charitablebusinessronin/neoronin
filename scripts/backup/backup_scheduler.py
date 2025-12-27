"""
Automated backup scheduler for Neo4j using APScheduler.

Runs as a sidecar container and executes:
- Scheduled full backups on cron schedule
- Periodic backup validation
- Automatic pruning of old backups
- Audit logging of backup operations
"""

import logging
import os
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from neo4j import GraphDatabase
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, '/app')

from scripts.backup.neo4j_backup import BackupManager
from src.durability.recovery import RecoveryStateMachine

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages automated backup scheduling and execution."""

    def __init__(self):
        """Initialize backup scheduler."""
        # Neo4j connection
        neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
        neo4j_password = os.environ.get('NEO4J_PASSWORD', 'changeme')

        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        # Backup configuration
        backup_dir = os.environ.get('BACKUP_DIR', '/app/backups')
        self.backup_manager = BackupManager(self.driver, backup_dir)
        self.recovery_machine = RecoveryStateMachine(self.driver)

        # Scheduler configuration
        self.scheduler = BackgroundScheduler()
        self.backup_schedule = os.environ.get('BACKUP_SCHEDULE', '0 2 * * *')  # 2 AM daily
        self.retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
        self.compress_backups = os.environ.get('BACKUP_COMPRESSION', 'true').lower() == 'true'

    def start(self):
        """Start the backup scheduler."""
        logger.info("Starting backup scheduler...")

        # Schedule backup job
        self.scheduler.add_job(
            self.run_backup,
            CronTrigger.from_crontab(self.backup_schedule),
            id='scheduled_backup',
            name='Scheduled Neo4j Backup',
            replace_existing=True
        )
        logger.info(f"Scheduled backup job with cron: {self.backup_schedule}")

        # Schedule validation job (run daily at 3 AM)
        self.scheduler.add_job(
            self.validate_recent_backups,
            CronTrigger.from_crontab('0 3 * * *'),
            id='backup_validation',
            name='Backup Validation',
            replace_existing=True
        )
        logger.info("Scheduled backup validation job")

        # Schedule pruning job (run weekly on Sunday at 4 AM)
        self.scheduler.add_job(
            self.prune_old_backups,
            CronTrigger.from_crontab('0 4 * * 0'),
            id='backup_pruning',
            name='Backup Pruning',
            replace_existing=True
        )
        logger.info(f"Scheduled backup pruning job (retention: {self.retention_days} days)")

        # Start scheduler
        self.scheduler.start()
        logger.info("Backup scheduler started successfully")

        # Keep scheduler running
        try:
            self.scheduler.print_jobs()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the backup scheduler."""
        logger.info("Stopping backup scheduler...")
        self.scheduler.shutdown()
        self.driver.close()
        logger.info("Backup scheduler stopped")

    def run_backup(self):
        """Execute a scheduled backup."""
        logger.info("Starting scheduled backup job...")

        try:
            # Check if recovery in progress
            recovery_state = self.recovery_machine.get_current_state()
            if recovery_state.get('status') in ['RECOVERING', 'VALIDATION']:
                logger.warning("Skipping scheduled backup - recovery in progress")
                return

            # Run backup
            success, message, metadata = self.backup_manager.create_backup(compress=self.compress_backups)

            if success:
                logger.info(f"Backup successful: {message}")
                self._log_backup_audit(
                    operation='BACKUP_CREATE',
                    result='SUCCESS',
                    backup_id=metadata.get('id'),
                    details=metadata
                )
            else:
                logger.error(f"Backup failed: {message}")
                self._log_backup_audit(
                    operation='BACKUP_CREATE',
                    result='FAILED',
                    details={'error': message}
                )

        except Exception as e:
            logger.error(f"Backup job error: {str(e)}")
            self._log_backup_audit(
                operation='BACKUP_CREATE',
                result='FAILED',
                details={'error': str(e)}
            )

    def validate_recent_backups(self):
        """Validate the most recent backups."""
        logger.info("Starting backup validation job...")

        try:
            backups = self.backup_manager.list_backups()

            # Validate the 3 most recent backups
            validated_count = 0
            for backup in backups[:3]:
                is_valid, message = self.backup_manager.validate_backup(backup['id'])

                if is_valid:
                    logger.info(f"Backup validation passed: {backup['id']}")
                    validated_count += 1
                else:
                    logger.error(f"Backup validation failed: {backup['id']} - {message}")

                self._log_backup_audit(
                    operation='BACKUP_VALIDATE',
                    result='SUCCESS' if is_valid else 'FAILED',
                    backup_id=backup['id'],
                    details={'message': message}
                )

            logger.info(f"Backup validation completed: {validated_count}/{len(backups[:3])} passed")

        except Exception as e:
            logger.error(f"Validation job error: {str(e)}")
            self._log_backup_audit(
                operation='BACKUP_VALIDATE',
                result='FAILED',
                details={'error': str(e)}
            )

    def prune_old_backups(self):
        """Prune backups older than retention period."""
        logger.info(f"Starting backup pruning job (retention: {self.retention_days} days)...")

        try:
            deleted_count, message = self.backup_manager.prune_old_backups(self.retention_days)

            logger.info(f"Backup pruning completed: {message}")
            self._log_backup_audit(
                operation='BACKUP_PRUNE',
                result='SUCCESS',
                details={'deleted_count': deleted_count, 'retention_days': self.retention_days}
            )

        except Exception as e:
            logger.error(f"Pruning job error: {str(e)}")
            self._log_backup_audit(
                operation='BACKUP_PRUNE',
                result='FAILED',
                details={'error': str(e)}
            )

    def _log_backup_audit(self, operation: str, result: str, backup_id: str = None, details: dict = None):
        """Log backup operation to audit log.

        Args:
            operation: Operation type (BACKUP_CREATE, BACKUP_VALIDATE, BACKUP_PRUNE)
            result: Operation result (SUCCESS, FAILED)
            backup_id: Affected backup ID (optional)
            details: Additional details (optional)
        """
        try:
            import uuid

            with self.driver.session() as session:
                session.run("""
                    CREATE (a:AuditLogEntry {
                        id: $id,
                        timestamp: $timestamp,
                        operation: $operation,
                        result: $result,
                        actor: 'backup-scheduler',
                        entity_type: 'BackupMetadata',
                        entity_id: $backup_id,
                        details: $details
                    })
                """,
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow().isoformat() + 'Z',
                    operation=operation,
                    result=result,
                    backup_id=backup_id,
                    details=str(details) if details else None
                )
        except Exception as e:
            logger.warning(f"Could not write audit log: {str(e)}")


def main():
    """Entry point for backup scheduler."""
    logger.info("Initializing backup scheduler...")

    try:
        scheduler = BackupScheduler()
        scheduler.start()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    import time
    main()
