"""
Neo4j backup tooling with metadata tracking and checksums.

Provides high-level backup operations wrapping neo4j-admin, including:
- Create new backups with validation
- List existing backups with metadata
- Delete old backups
- Validate backup integrity
"""

import logging
import os
import subprocess
import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages Neo4j backups with metadata tracking."""

    def __init__(self, driver: Driver, backup_dir: str):
        """Initialize backup manager.

        Args:
            driver: Neo4j driver connection
            backup_dir: Directory where backups are stored
        """
        self.driver = driver
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, backup_id: Optional[str] = None, compress: bool = True) -> Tuple[bool, str, Dict]:
        """Create a new backup of the Neo4j database.

        Args:
            backup_id: Custom backup identifier (auto-generated if None)
            compress: Whether to compress the backup

        Returns:
            Tuple[bool, str, Dict]: (success, message, metadata)
        """
        start_time = time.time()

        # Generate backup ID if not provided
        if not backup_id:
            backup_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        backup_path = self.backup_dir / backup_id

        try:
            # Check if backup already exists
            if backup_path.exists():
                return False, f"Backup {backup_id} already exists", {}

            # Create backup using APOC (Logical Backup)
            # Note: We write to the default import dir, which is now mounted to our shared backup volume
            backup_filename = f"{backup_id}.graphml"
            neo4j_internal_path = backup_filename
            
            logger.info(f"Starting APOC backup {backup_id} to {neo4j_internal_path}...")
            
            with self.driver.session() as session:
                result = session.run("""
                    CALL apoc.export.graphml.all($file, {useTypes:true, readLabels:true})
                """, file=neo4j_internal_path).single()
                
                if not result:
                     raise Exception("APOC export returned no result")

            # Check if file ultimately appeared in our view of the volume
            # The scheduler mounts the same volume at self.backup_dir
             # Wait briefly for I/O sync if needed (usually instant on local docker volume)
            expected_local_file = self.backup_dir / backup_filename
            if not expected_local_file.exists():
                 # Small race condition or mount issue?
                 time.sleep(1)
            
            if not expected_local_file.exists():
                return False, f"Backup file {expected_local_file} not found after APOC export", {}

            # Create a directory for this backup ID to match expected structure (or just use the file?)
            # The previous code expected a directory. Let's adapt to be a directory containing the file
            # to keep the rest of the metadata logic similar, or calculate checksum on the file.
            
            # Move the file into a directory named backup_id
            backup_path.mkdir(exist_ok=True)
            new_file_path = backup_path / backup_filename
            expected_local_file.rename(new_file_path)

            # Calculate checksum
            logger.info(f"Calculating checksum for {backup_id}...")
            checksum = self._calculate_checksum(backup_path)

            # Get backup size
            size_bytes = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())

            # Create metadata
            duration_seconds = int(time.time() - start_time)
            metadata = {
                'id': backup_id,
                'timestamp_created': datetime.utcnow().isoformat() + 'Z',
                'status': 'completed',
                'backup_file': str(backup_path),
                'size_bytes': size_bytes,
                'checksum': checksum,
                'duration_seconds': duration_seconds,
                'compressed': compress,
                'neo4j_version': self._get_neo4j_version()
            }

            # Persist metadata to Neo4j
            self._save_backup_metadata(metadata)

            logger.info(f"Backup {backup_id} completed successfully ({size_bytes} bytes)")
            return True, f"Backup {backup_id} created successfully", metadata

        except subprocess.TimeoutExpired:
            return False, f"Backup timeout after 600 seconds", {}
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            return False, f"Backup failed: {str(e)}", {}

    def list_backups(self) -> List[Dict]:
        """List all available backups with metadata.

        Returns:
            List[Dict]: List of backup metadata dictionaries
        """
        try:
            backups = []

            # Query backup metadata from Neo4j
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (b:BackupMetadata)
                    RETURN b {.*,
                             id: b.id,
                             timestamp_created: b.timestamp_created,
                             status: b.status,
                             size_bytes: b.size_bytes,
                             checksum: b.checksum} as metadata
                    ORDER BY b.timestamp_created DESC
                """)

                for record in result:
                    backups.append(dict(record['metadata']))

            logger.info(f"Found {len(backups)} backups")
            return backups

        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            return []

    def delete_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Delete a backup and its metadata.

        Args:
            backup_id: ID of backup to delete

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            backup_path = self.backup_dir / backup_id

            # Check if backup exists
            if not backup_path.exists():
                return False, f"Backup {backup_id} not found"

            # Delete from filesystem
            import shutil
            shutil.rmtree(backup_path)
            logger.info(f"Deleted backup directory: {backup_path}")

            # Delete metadata from Neo4j
            with self.driver.session() as session:
                session.run("""
                    MATCH (b:BackupMetadata {id: $backup_id})
                    DELETE b
                """, backup_id=backup_id)

            logger.info(f"Deleted backup {backup_id}")
            return True, f"Backup {backup_id} deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting backup: {str(e)}")
            return False, f"Error deleting backup: {str(e)}"

    def validate_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Validate backup integrity using checksums.

        Args:
            backup_id: ID of backup to validate

        Returns:
            Tuple[bool, str]: (valid, message)
        """
        try:
            backup_path = self.backup_dir / backup_id

            if not backup_path.exists():
                return False, f"Backup {backup_id} not found"

            # Get stored checksum from metadata
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (b:BackupMetadata {id: $backup_id})
                    RETURN b.checksum as stored_checksum
                """, backup_id=backup_id).single()

                if not result:
                    return False, f"Backup metadata not found for {backup_id}"

                stored_checksum = result['stored_checksum']

            # Calculate current checksum
            current_checksum = self._calculate_checksum(backup_path)

            if stored_checksum == current_checksum:
                logger.info(f"Backup {backup_id} validation passed")
                return True, f"Backup {backup_id} validation passed (checksum match)"
            else:
                logger.error(f"Backup {backup_id} validation failed - checksum mismatch")
                return False, f"Backup {backup_id} validation failed - checksum mismatch"

        except Exception as e:
            logger.error(f"Error validating backup: {str(e)}")
            return False, f"Error validating backup: {str(e)}"

    def prune_old_backups(self, retention_days: int) -> Tuple[int, str]:
        """Delete backups older than retention period.

        Args:
            retention_days: Number of days to retain backups

        Returns:
            Tuple[int, str]: (number_deleted, message)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            deleted_count = 0

            backups = self.list_backups()

            for backup in backups:
                backup_time = datetime.fromisoformat(backup['timestamp_created'].replace('Z', '+00:00'))

                if backup_time < cutoff_date:
                    success, msg = self.delete_backup(backup['id'])
                    if success:
                        deleted_count += 1
                        logger.info(f"Pruned backup {backup['id']}")

            return deleted_count, f"Pruned {deleted_count} backups older than {retention_days} days"

        except Exception as e:
            logger.error(f"Error pruning backups: {str(e)}")
            return 0, f"Error pruning backups: {str(e)}"

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of a directory.

        Args:
            path: Path to directory

        Returns:
            str: Hex checksum
        """
        hasher = hashlib.sha256()

        for file_path in sorted(path.rglob('*')):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())

        return hasher.hexdigest()

    def _save_backup_metadata(self, metadata: Dict) -> None:
        """Persist backup metadata to Neo4j.

        Args:
            metadata: Backup metadata dictionary
        """
        with self.driver.session() as session:
            session.run("""
                MERGE (b:BackupMetadata {id: $id})
                SET b.timestamp_created = $timestamp_created,
                    b.status = $status,
                    b.backup_file = $backup_file,
                    b.size_bytes = $size_bytes,
                    b.checksum = $checksum,
                    b.duration_seconds = $duration_seconds,
                    b.compressed = $compressed,
                    b.neo4j_version = $neo4j_version
            """, **metadata)

    def _get_neo4j_version(self) -> str:
        """Get Neo4j database version.

        Returns:
            str: Version string
        """
        try:
            with self.driver.session() as session:
                result = session.run("RETURN apoc.version() as version").single()
                if result:
                    return str(result['version'])
        except:
            pass

        return "unknown"
