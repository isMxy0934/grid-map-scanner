import unittest
import os
import shutil
import json
from unittest.mock import patch, MagicMock

from corner_store_scanner.main import MainScanner
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.session_manager import ScanSessionManager
from corner_store_scanner.file_storage import LocalFileStorage
from corner_store_scanner.models import PlaceData, Coordinate

class TestIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a clean environment for each integration test."""
        self.test_data_dir = "test_integration_data"
        # Clean up any previous test runs
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)
        os.makedirs(self.test_data_dir, exist_ok=True)

        self.config = ScanConfig(
            center_latitude=34.0522,  # Los Angeles
            center_longitude=-118.2437,
            scan_radius_km=0.5,  # Very small radius for testing
            MAX_BUDGET=0.50,  # Low budget to prevent real cost
            MACRO_GRID_SPACING=0.2,
            FINE_GRID_SPACING=0.1,
            MACRO_SEARCH_RADIUS=150,
            FINE_SEARCH_RADIUS=75,
            RECURSION_TRIGGER_COUNT=2 # Lower for testing recursion
        )

        # IMPORTANT: Override the default data directory to isolate test artifacts
        self.data_dir_patcher = patch.object(LocalFileStorage, 'data_dir', self.test_data_dir)
        self.data_dir_patcher.start()
        self.addCleanup(self.data_dir_patcher.stop)

        self.session_dir_patcher = patch.object(LocalFileStorage, 'session_dir', os.path.join(self.test_data_dir, 'sessions'))
        self.session_dir_patcher.start()
        self.addCleanup(self.session_dir_patcher.stop)

        self.session_dir_patcher = patch.object(LocalFileStorage, 'session_dir', os.path.join(self.test_data_dir, 'sessions'))
        self.session_dir_patcher.start()
        self.addCleanup(self.session_dir_patcher.stop)

        self.session_dir_patcher = patch.object(LocalFileStorage, 'session_dir', os.path.join(self.test_data_dir, 'sessions'))
        self.session_dir_patcher.start()
        self.addCleanup(self.session_dir_patcher.stop)

    def tearDown(self):
        """Clean up the test data directory after each test."""
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    @patch('corner_store_scanner.places_client.PlacesAPIClient.nearby_search')
    @patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "test_api_key"})
    def test_full_scan_and_resume_flow(self, mock_nearby_search):
        """
        Test the full end-to-end scan process, including session resumption.
        """
        # --- Mock API Responses ---
        # This is crucial to simulate API behavior without actual calls.

        # Mock response for a macro point that triggers a fine scan
        mock_hotspot_response = [
            PlaceData(place_id="macro_place_1", name="Hotspot Store 1", types=['convenience_store'], formatted_address="123 Main St", latitude=34.05, longitude=-118.24, postal_address="", photos=[], grid_point_id="", scan_time="", scan_level=0),
            PlaceData(place_id="macro_place_2", name="Hotspot Store 2", types=['convenience_store'], formatted_address="124 Main St", latitude=34.05, longitude=-118.24, postal_address="", photos=[], grid_point_id="", scan_time="", scan_level=0)
        ]

        # Mock response for a fine point that triggers recursion
        mock_extreme_density_response = [
            PlaceData(place_id="fine_place_1", name="Extreme Store 1", types=['convenience_store'], formatted_address="456 Side St", latitude=34.051, longitude=-118.241, postal_address="", photos=[], grid_point_id="", scan_time="", scan_level=0),
            PlaceData(place_id="fine_place_2", name="Extreme Store 2", types=['convenience_store'], formatted_address="457 Side St", latitude=34.051, longitude=-118.241, postal_address="", photos=[], grid_point_id="", scan_time="", scan_level=0)
        ]
        
        # Mock response for a recursive (enhanced) scan point
        mock_enhanced_response = [
            PlaceData(place_id="enhanced_place_1", name="Deep Store", types=['convenience_store'], formatted_address="789 Deep Ave", latitude=34.0511, longitude=-118.2411, postal_address="", photos=[], grid_point_id="", scan_time="", scan_level=0)
        ]

        # Mock response for a normal, low-density point
        mock_normal_response = [
            PlaceData(place_id="normal_place_1", name="Quiet Store", types=['convenience_store'], formatted_address="101 Low St", latitude=34.052, longitude=-118.242, postal_address="", photos=[], grid_point_id="", scan_time="", scan_level=0)
        ]

        # Set the side_effect to return different values on subsequent calls
        mock_nearby_search.side_effect = [
            mock_hotspot_response,  # First macro call is a hotspot
            mock_normal_response,  # Other macro calls are normal
            mock_normal_response,
            mock_normal_response,
            mock_extreme_density_response,  # First fine call is extreme density
            mock_normal_response,  # Other fine calls are normal
            mock_enhanced_response,  # The enhanced (recursive) call
            mock_normal_response,  # Subsequent calls
            mock_normal_response,
            mock_normal_response,
        ] * 200  # Repeat to ensure we don't run out of mocks

        # --- Phase 1: Run the initial scan ---
        scanner = MainScanner(config=self.config)
        session_id = scanner.session_id
        scanner.run_scan()

        # --- Verification for Phase 1 ---
        self.assertTrue(mock_nearby_search.call_count > 5) # Ensure multiple stages ran
        
        # Check that results were saved
        results_file = os.path.join(self.test_data_dir, session_id, "places_results.csv")
        self.assertTrue(os.path.exists(results_file))
        with open(results_file, 'r') as f:
            content = f.read()
            self.assertIn("macro_place_1", content)
            self.assertIn("fine_place_1", content)
            self.assertIn("enhanced_place_1", content)

        # Check that the session is marked as completed
        session_manager = ScanSessionManager(self.config)
        session_data = session_manager.load_session(session_id)
        self.assertTrue(session_data['is_completed'])

        # --- Phase 2: Test Resumption (on a new, incomplete session) ---
        
        # Let's create a new session and manually mark it as incomplete
        # to simulate a crash.
        resume_config = self.config
        resume_session_id = "resume_test_session"
        scanner_for_resume = MainScanner(config=resume_config, session_id=resume_session_id)
        
        # Manually save some progress to simulate a partial run
        scanner_for_resume.completed_grid_points.add("M-34.05-118.24-150")
        scanner_for_resume.total_places_found = 2
        scanner_for_resume.api_call_count = 1
        scanner_for_resume.current_session.completed_grid_points = scanner_for_resume.completed_grid_points
        scanner_for_resume.current_session.total_places_found = 2
        scanner_for_resume.current_session.total_api_calls = 1
        scanner_for_resume.session_manager.save_session_state(resume_session_id, scanner_for_resume.current_session.to_dict())

        # Now, create a new MainScanner instance to test if it resumes correctly
        resumed_scanner = MainScanner(config=resume_config, session_id=resume_session_id)
        
        # --- Verification for Phase 2 ---
        self.assertEqual(len(resumed_scanner.completed_grid_points), 1)
        self.assertEqual(resumed_scanner.total_places_found, 2)
        self.assertEqual(resumed_scanner.api_call_count, 1)
        self.assertEqual(resumed_scanner.session_id, resume_session_id)
        self.assertFalse(resumed_scanner.current_session.is_completed)
        
        # Run the resumed scan to completion
        resumed_scanner.run_scan()
        
        # Verify it completed
        resumed_session_data = session_manager.load_session(resume_session_id)
        self.assertTrue(resumed_session_data['is_completed'])

if __name__ == '__main__':
    unittest.main()
