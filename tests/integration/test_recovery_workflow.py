"""
Integration tests for recovery workflow (User Story 2).

Tests the recovery state machine and restore operations:
1. Recovery state transitions
2. Backup restoration
3. Validation after restore
4. Promotion to production
5. Rollback on failure
"""

import pytest
import time
from neo4j import GraphDatabase
from src.durability.recovery import RecoveryStateMachine, RecoveryStatus


class TestRecoveryStateMachine:
    """Test suite for recovery state machine."""

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
    def recovery_machine(self, neo4j_driver):
        """Create recovery state machine."""
        return RecoveryStateMachine(neo4j_driver)

    def test_initial_recovery_state(self, recovery_machine):
        """Test initial recovery state is NOT_RECOVERING."""
        state = recovery_machine.get_current_state()

        # State should be empty or in NOT_RECOVERING state
        if state:
            assert state.get('status') in [RecoveryStatus.NOT_RECOVERING.value, 'NOT_RECOVERING']

    def test_initialize_recovery(self, recovery_machine):
        """Test initializing a recovery operation."""
        # Reset state first
        recovery_machine.reset_recovery_state()

        # Initialize recovery
        result = recovery_machine.initialize_recovery('test-backup-001')

        assert result is True

        # Verify state
        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.RECOVERING.value
        assert state['backup_id'] == 'test-backup-001'
        assert state['progress_percent'] == 0

    def test_prevent_concurrent_recovery(self, recovery_machine):
        """Test that concurrent recovery operations are prevented."""
        # Reset state first
        recovery_machine.reset_recovery_state()

        # Initialize first recovery
        assert recovery_machine.initialize_recovery('backup-1') is True

        # Try to initialize second recovery - should fail
        result = recovery_machine.initialize_recovery('backup-2')
        assert result is False

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_update_progress(self, recovery_machine):
        """Test updating recovery progress."""
        # Reset and initialize
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-002')

        # Update progress
        recovery_machine.update_progress(25)

        state = recovery_machine.get_current_state()
        assert state['progress_percent'] == 25

        # Update again
        recovery_machine.update_progress(50)
        state = recovery_machine.get_current_state()
        assert state['progress_percent'] == 50

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_progress_bounds(self, recovery_machine):
        """Test that progress is bounded to 0-100."""
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-003')

        # Try to set progress > 100
        recovery_machine.update_progress(150)
        state = recovery_machine.get_current_state()
        assert state['progress_percent'] == 100

        # Try to set progress < 0
        recovery_machine.update_progress(-50)
        state = recovery_machine.get_current_state()
        assert state['progress_percent'] == 0

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_start_validation_phase(self, recovery_machine):
        """Test transitioning to validation phase."""
        # Reset and initialize
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-004')

        # Update to near completion
        recovery_machine.update_progress(90)

        # Start validation
        recovery_machine.start_validation()

        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.VALIDATION.value
        assert state['progress_percent'] == 100

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_validation_passed(self, recovery_machine):
        """Test marking validation as passed."""
        # Setup: Initialize and move to validation
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-005')
        recovery_machine.update_progress(90)
        recovery_machine.start_validation()

        # Mark validation as passed
        recovery_machine.validation_passed()

        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.RECOVERY_SUCCESS.value
        assert 'completed_at' in state

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_validation_failed(self, recovery_machine):
        """Test marking validation as failed."""
        # Setup: Initialize and move to validation
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-006')
        recovery_machine.update_progress(50)
        recovery_machine.start_validation()

        # Mark validation as failed
        errors = ['Schema mismatch', 'Orphaned relationships found']
        recovery_machine.validation_failed(errors)

        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.RECOVERY_FAILED.value
        assert 'validation_errors' in state
        assert len(state['validation_errors']) == 2

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_promote_to_production(self, recovery_machine):
        """Test promoting successful recovery to production."""
        # Setup: Initialize, validate, and pass validation
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-007')
        recovery_machine.update_progress(90)
        recovery_machine.start_validation()
        recovery_machine.validation_passed()

        # Promote to production
        result = recovery_machine.promote_to_production()

        assert result is True

        state = recovery_machine.get_current_state()
        assert state.get('promoted_to_production') is True
        assert 'promoted_at' in state

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_cannot_promote_without_success(self, recovery_machine):
        """Test that promotion fails if recovery not in success state."""
        # Initialize but don't complete validation
        recovery_machine.reset_recovery_state()
        recovery_machine.initialize_recovery('test-backup-008')

        result = recovery_machine.promote_to_production()

        assert result is False

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_reset_recovery_state(self, recovery_machine):
        """Test resetting recovery state."""
        # Initialize and update
        recovery_machine.initialize_recovery('test-backup-009')
        recovery_machine.update_progress(50)

        # Reset
        recovery_machine.reset_recovery_state()

        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.NOT_RECOVERING.value
        assert state.get('backup_id') is None
        assert state['progress_percent'] == 0

    def test_full_recovery_workflow(self, recovery_machine):
        """Test complete recovery workflow from start to production."""
        # Initialize
        assert recovery_machine.initialize_recovery('test-backup-010') is True

        # Simulate restore progress
        for progress in [0, 25, 50, 75, 90]:
            recovery_machine.update_progress(progress)

        # Start validation
        recovery_machine.start_validation()
        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.VALIDATION.value

        # Pass validation
        recovery_machine.validation_passed()
        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.RECOVERY_SUCCESS.value

        # Promote to production
        assert recovery_machine.promote_to_production() is True
        state = recovery_machine.get_current_state()
        assert state.get('promoted_to_production') is True

        # Cleanup
        recovery_machine.reset_recovery_state()

    def test_recovery_failure_workflow(self, recovery_machine):
        """Test recovery workflow when validation fails."""
        # Initialize
        recovery_machine.initialize_recovery('test-backup-011')
        recovery_machine.update_progress(50)
        recovery_machine.start_validation()

        # Fail validation
        recovery_machine.validation_failed(['Data integrity check failed'])
        state = recovery_machine.get_current_state()
        assert state['status'] == RecoveryStatus.RECOVERY_FAILED.value

        # Cannot promote after failure
        assert recovery_machine.promote_to_production() is False

        # Cleanup
        recovery_machine.reset_recovery_state()


class TestRecoveryStateTransitions:
    """Test recovery state transition rules."""

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
    def recovery_machine(self, neo4j_driver):
        """Create recovery state machine."""
        return RecoveryStateMachine(neo4j_driver)

    def test_invalid_state_transition(self, recovery_machine):
        """Test that invalid state transitions are prevented."""
        recovery_machine.reset_recovery_state()

        # Try to transition from NOT_RECOVERING to VALIDATION (invalid)
        recovery_machine.start_validation()  # This should not change state

        state = recovery_machine.get_current_state()
        # Should remain in NOT_RECOVERING since we can't transition directly
        assert state['status'] == RecoveryStatus.NOT_RECOVERING.value

    def test_state_transitions_timeline(self, recovery_machine):
        """Test that states transition in correct timeline."""
        recovery_machine.reset_recovery_state()

        states_seen = []

        # Track state after each operation
        recovery_machine.initialize_recovery('test-backup-012')
        state = recovery_machine.get_current_state()
        states_seen.append(state['status'])

        recovery_machine.update_progress(80)
        state = recovery_machine.get_current_state()
        states_seen.append(state['status'])

        recovery_machine.start_validation()
        state = recovery_machine.get_current_state()
        states_seen.append(state['status'])

        recovery_machine.validation_passed()
        state = recovery_machine.get_current_state()
        states_seen.append(state['status'])

        # Verify sequence
        expected = [
            RecoveryStatus.RECOVERING.value,
            RecoveryStatus.RECOVERING.value,
            RecoveryStatus.VALIDATION.value,
            RecoveryStatus.RECOVERY_SUCCESS.value
        ]

        assert states_seen == expected

        # Cleanup
        recovery_machine.reset_recovery_state()
