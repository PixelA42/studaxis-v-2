"""
Test that services which should be offline when the network is gone
actually report and behave as offline.

Services under test:
  - SyncOrchestrator.is_online() → False when connectivity check fails
  - SyncOrchestrator state → OFFLINE after network loss
  - ConflictAwareOrchestrator.is_online() → False when base is offline
"""

import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sync_orchestrator import SyncOrchestrator


class TestServicesOfflineWhenNetworkGone(unittest.TestCase):
    """Verify sync-related services report offline when network is gone."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="studaxis_offline_services_")

    def tearDown(self):
        try:
            orchestrator = getattr(self, "orchestrator", None)
            if orchestrator and hasattr(orchestrator, "cleanup"):
                orchestrator.cleanup()
        finally:
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sync_orchestrator_is_offline_when_connectivity_returns_false(self):
        """When connectivity check fails (network gone), SyncOrchestrator reports offline."""
        orchestrator = SyncOrchestrator(base_path=self.test_dir)
        self.orchestrator = orchestrator

        with patch.object(orchestrator.sync_manager, "check_connectivity", return_value=False):
            self.assertFalse(
                orchestrator.is_online(),
                "SyncOrchestrator.is_online() should be False when network is gone",
            )

    def test_sync_orchestrator_is_online_when_connectivity_returns_true(self):
        """When connectivity check succeeds, SyncOrchestrator reports online (sanity check)."""
        orchestrator = SyncOrchestrator(base_path=self.test_dir)
        self.orchestrator = orchestrator

        with patch.object(orchestrator.sync_manager, "check_connectivity", return_value=True):
            self.assertTrue(
                orchestrator.is_online(),
                "SyncOrchestrator.is_online() should be True when network is available",
            )

    def test_sync_orchestrator_state_offline_after_network_loss(self):
        """After network loss is handled, orchestrator state is OFFLINE and is_online() is False."""
        orchestrator = SyncOrchestrator(base_path=self.test_dir)
        self.orchestrator = orchestrator

        # Start in a state that can transition to OFFLINE (e.g. SYNCING or QUEUED)
        orchestrator.state = "QUEUED"
        orchestrator._save_state()

        orchestrator._handle_network_loss()

        self.assertEqual(
            orchestrator.get_state(),
            "OFFLINE",
            "State should be OFFLINE after network loss",
        )
        with patch.object(orchestrator.sync_manager, "check_connectivity", return_value=False):
            self.assertFalse(
                orchestrator.is_online(),
                "is_online() should be False when network is gone",
            )

    def test_sync_orchestrator_execute_sync_reports_offline_when_network_gone(self):
        """execute_sync() result has online=False when connectivity is down."""
        orchestrator = SyncOrchestrator(base_path=self.test_dir)
        self.orchestrator = orchestrator

        with patch.object(orchestrator.sync_manager, "check_connectivity", return_value=False):
            orchestrator.state = "OFFLINE"
            orchestrator._save_state()

            result = orchestrator.execute_sync()

        self.assertFalse(
            result.get("online", True),
            "execute_sync() result should have online=False when offline",
        )
        self.assertIn("Cannot sync while offline", result.get("errors", []))


class TestConflictAwareOrchestratorOfflineWhenNetworkGone(unittest.TestCase):
    """ConflictAwareOrchestrator should report offline when base orchestrator is offline."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="studaxis_offline_services_")

    def tearDown(self):
        try:
            orchestrator = getattr(self, "orchestrator", None)
            if orchestrator and hasattr(orchestrator, "base_orchestrator"):
                base = orchestrator.base_orchestrator
                if hasattr(base, "cleanup"):
                    base.cleanup()
        finally:
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_conflict_aware_orchestrator_is_offline_when_network_gone(self):
        """When network is gone, ConflictAwareOrchestrator.is_online() is False."""
        from conflict_resolution_engine import ConflictAwareOrchestrator

        orchestrator = ConflictAwareOrchestrator(base_path=self.test_dir)
        self.orchestrator = orchestrator

        with patch.object(
            orchestrator.base_orchestrator.sync_manager,
            "check_connectivity",
            return_value=False,
        ):
            self.assertFalse(
                orchestrator.is_online(),
                "ConflictAwareOrchestrator.is_online() should be False when network is gone",
            )


if __name__ == "__main__":
    unittest.main()
