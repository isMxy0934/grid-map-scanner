import unittest
import os
import shutil
import json
from datetime import datetime
from unittest.mock import patch

from corner_store_scanner.config import ScanConfig
from corner_store_scanner.session_manager import ScanSessionManager

class TestScanSessionManager(unittest.TestCase):

    def setUp(self):
        self.config = ScanConfig()
        self.test_sessions_dir = "test_sessions"
        # Override the sessions_dir for testing purposes
        self.manager = ScanSessionManager(self.config)
        self.manager.sessions_dir = self.test_sessions_dir
        
    def tearDown(self):
        # Clean up the created test directories and files
        if os.path.exists(self.test_sessions_dir):
            shutil.rmtree(self.test_sessions_dir)

    def test_ensure_sessions_directory(self):
        """Test that the sessions directory is created on initialization."""
        self.manager.ensure_sessions_directory()
        self.assertTrue(os.path.isdir(self.test_sessions_dir))

    @patch('corner_store_scanner.session_manager.datetime')
    def test_generate_session_id(self, mock_datetime):
        """Test that a unique session ID is generated correctly."""
        # Mock datetime to ensure consistent ID generation for testing
        mock_datetime.now.return_value = datetime(2025, 7, 17, 10, 30, 0)
        mock_datetime.strftime.side_effect = lambda *args, **kw: datetime(2025, 7, 17, 10, 30, 0).strftime(*args, **kw)

        session_id = self.manager.generate_session_id()
        self.assertEqual(session_id, "scan_20250717_103000")

    @patch('corner_store_scanner.session_manager.datetime')
    def test_create_new_session(self, mock_datetime):
        """Test creating a new scan session."""
        mock_datetime.now.return_value = datetime(2025, 7, 17, 10, 30, 0)
        mock_datetime.isoformat.return_value = "2025-07-17T10:30:00"

        session_id = "test_session_1"
        session_state = self.manager.create_new_session(session_id)

        session_path = os.path.join(self.test_sessions_dir, session_id)
        self.assertTrue(os.path.isdir(session_path))
        self.assertTrue(os.path.isfile(os.path.join(session_path, "config.json")))
        self.assertTrue(os.path.isfile(os.path.join(session_path, "session_state.json")))

        self.assertEqual(session_state["session_id"], session_id)
        self.assertEqual(session_state["status"], "in_progress")
        self.assertIn("config_snapshot_file", session_state)
        
        # Verify saved config snapshot
        with open(os.path.join(session_path, "config.json"), 'r') as f:
            saved_config = json.load(f)
            self.assertEqual(saved_config["center_latitude"], self.config.center_latitude)

        # Verify saved session state
        with open(os.path.join(session_path, "session_state.json"), 'r') as f:
            saved_state = json.load(f)
            self.assertEqual(saved_state["session_id"], session_id)

    def test_save_and_load_session_state(self):
        """Test saving and loading session state."""
        session_id = "test_session_2"
        self.manager.ensure_sessions_directory() # Ensure base dir exists for test
        session_path = os.path.join(self.test_sessions_dir, session_id)
        os.makedirs(session_path) # Create session-specific dir

        state_to_save = {"session_id": session_id, "status": "completed", "progress": {"grid_1": True}}
        self.manager.save_session_state(session_id, state_to_save)

        loaded_state = self.manager.load_session(session_id)
        self.assertEqual(loaded_state, state_to_save)

    def test_load_non_existent_session(self):
        """Test loading a session that does not exist."""
        loaded_state = self.manager.load_session("non_existent_session")
        self.assertIsNone(loaded_state)

    def test_list_available_sessions(self):
        """Test listing available sessions."""
        self.manager.ensure_sessions_directory()
        os.makedirs(os.path.join(self.test_sessions_dir, "session_A"))
        os.makedirs(os.path.join(self.test_sessions_dir, "session_B"))
        # Create a file to ensure it's not listed as a session
        with open(os.path.join(self.test_sessions_dir, "not_a_session.txt"), 'w') as f:
            f.write("test")

        sessions = self.manager.list_available_sessions()
        self.assertIn("session_A", sessions)
        self.assertIn("session_B", sessions)
        self.assertNotIn("not_a_session.txt", sessions)
        self.assertEqual(len(sessions), 2)

    def test_check_config_compatibility(self):
        """Test checking config compatibility."""
        session_id = "test_session_compat"
        # Create a session with a known config
        mock_config = ScanConfig()
        mock_config.center_latitude = 1.0
        mock_config.center_longitude = 2.0
        mock_config.scan_radius_km = 10
        mock_config.PLACE_TYPES = ["store"]

        self.manager.ensure_sessions_directory()
        session_path = os.path.join(self.test_sessions_dir, session_id)
        os.makedirs(session_path)
        config_snapshot_path = os.path.join(session_path, "config.json")
        with open(config_snapshot_path, 'w') as f:
            json.dump(mock_config.to_dict(), f)

        # Test compatible config
        compatible_config = ScanConfig()
        compatible_config.center_latitude = 1.0
        compatible_config.center_longitude = 2.0
        compatible_config.scan_radius_km = 10
        compatible_config.PLACE_TYPES = ["store"]
        self.assertTrue(self.manager.check_config_compatibility(session_id, compatible_config))

        # Test incompatible config (different radius)
        incompatible_config = ScanConfig()
        incompatible_config.center_latitude = 1.0
        incompatible_config.center_longitude = 2.0
        incompatible_config.scan_radius_km = 20 # Different
        incompatible_config.PLACE_TYPES = ["store"]
        self.assertFalse(self.manager.check_config_compatibility(session_id, incompatible_config))

        # Test incompatible config (missing config file)
        self.assertFalse(self.manager.check_config_compatibility("non_existent_session", compatible_config))
        
    def test_cleanup_completed_sessions(self):
        """Test cleaning up completed or failed sessions."""
        self.manager.ensure_sessions_directory()

        # Create a completed session
        completed_session_id = "completed_session"
        completed_session_path = os.path.join(self.test_sessions_dir, completed_session_id)
        os.makedirs(completed_session_path)
        with open(os.path.join(completed_session_path, "session_state.json"), 'w') as f:
            json.dump({"status": "completed"}, f)

        # Create a failed session
        failed_session_id = "failed_session"
        failed_session_path = os.path.join(self.test_sessions_dir, failed_session_id)
        os.makedirs(failed_session_path)
        with open(os.path.join(failed_session_path, "session_state.json"), 'w') as f:
            json.dump({"status": "failed"}, f)

        # Create an in_progress session (should not be cleaned)
        in_progress_session_id = "in_progress_session"
        in_progress_session_path = os.path.join(self.test_sessions_dir, in_progress_session_id)
        os.makedirs(in_progress_session_path)
        with open(os.path.join(in_progress_session_path, "session_state.json"), 'w') as f:
            json.dump({"status": "in_progress"}, f)

        self.manager.cleanup_completed_sessions()

        self.assertFalse(os.path.exists(completed_session_path))
        self.assertFalse(os.path.exists(failed_session_path))
        self.assertTrue(os.path.exists(in_progress_session_path))

if __name__ == '__main__':
    unittest.main()
