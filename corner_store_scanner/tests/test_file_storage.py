import unittest
import os
import shutil
import json
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.file_storage import LocalFileStorage
from corner_store_scanner.models import PlaceData, GridPoint, Coordinate

class TestFileStorage(unittest.TestCase):

    def setUp(self):
        self.config = ScanConfig()
        self.session_id = "test_session_123"
        self.test_data_dir = "test_data"
        
        # Ensure the test_data_dir is clean before starting each test
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

        # Override the data_dir for testing purposes
        self.storage = LocalFileStorage(self.config, self.session_id)
        self.storage.data_dir = self.test_data_dir
        self.storage.session_dir = os.path.join(self.test_data_dir, self.session_id)
        
        # Rea_initialize file paths within the storage instance after overriding directories
        self.storage.places_file = os.path.join(self.storage.session_dir, "places_results.csv")
        self.storage.progress_file = os.path.join(self.storage.session_dir, "progress.json")
        self.storage.failed_log_file = os.path.join(self.storage.session_dir, "failed.log")
        self.storage.summary_file = os.path.join(self.storage.session_dir, "scan_summary.json")

        # Ensure directories are created for this specific test run
        self.storage.ensure_data_directories()
        
    def tearDown(self):
        # Clean up the created test directories and files
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def test_directory_creation(self):
        """Test that the data and session directories are created on initialization."""
        self.storage.ensure_data_directories()
        self.assertTrue(os.path.isdir(self.test_data_dir))
        self.assertTrue(os.path.isdir(self.storage.session_dir))

    def test_save_places(self):
        """Test saving place data to a CSV file."""
        # Create a couple of dummy PlaceData objects
        places = [
            PlaceData("id1", "Store 1", "Addr 1", 34.0, -118.0, "90210", ["store"], [], "grid1", "time1", 1),
            PlaceData("id2", "Store 2", "Addr 2", 34.1, -118.1, "90211", ["store"], [], "grid1", "time2", 1)
        ]
        
        self.storage.save_places(places)
        
        # Verify the file was created and has content
        self.assertTrue(os.path.isfile(self.storage.places_file))
        with open(self.storage.places_file, 'r') as f:
            content = f.read()
            self.assertIn("place_id,name,formatted_address", content) # Header
            self.assertIn("id1,Store 1", content)
            self.assertIn("id2,Store 2", content)

    def test_save_progress(self):
        """Test saving a completed grid point ID."""
        self.storage.save_progress("grid_point_123")
        self.assertTrue(os.path.isfile(self.storage.progress_file))
        with open(self.storage.progress_file, 'r') as f:
            self.assertIn("grid_point_123", f.read())

    def test_log_failed_point(self):
        """Test logging a failed grid point."""
        from corner_store_scanner.models import GridPoint, Coordinate
        point = GridPoint(center=Coordinate(0,0), radius=100, level=1)
        self.storage.log_failed_point(point, "Test Error")
        self.assertTrue(os.path.isfile(self.storage.failed_log_file))
        with open(self.storage.failed_log_file, 'r') as f:
            self.assertIn(f"{point.id} - Test Error", f.read())

    def test_load_progress(self):
        """Test loading progress from a file."""
        # First, save some progress
        self.storage.save_progress("grid1")
        self.storage.save_progress("grid2")
        
        progress_set = self.storage.load_progress()
        self.assertEqual(progress_set, {"grid1", "grid2"})

    def test_load_progress_no_file(self):
        """Test loading progress when the file doesn't exist."""
        progress_set = self.storage.load_progress()
        self.assertEqual(progress_set, set())

    def test_generate_summary_report(self):
        """Test the generation of the final summary report."""
        # Create some dummy files to be summarized
        with open(self.storage.places_file, 'w') as f:
            f.write("header\nline1\nline2") # 3 lines = 2 places
        with open(self.storage.failed_log_file, 'w') as f:
            f.write("failure1\n") # 1 failed point

        summary = self.storage.generate_summary_report(
            total_places=100,
            total_api_calls=50,
            failed_points=5,
            scan_duration_seconds=1234.5
        )

        self.assertTrue(os.path.isfile(self.storage.summary_file))
        self.assertEqual(summary['total_places_found'], 100)
        self.assertEqual(summary['total_api_calls'], 50)
        self.assertEqual(summary['failed_grid_points'], 5)
        
        with open(self.storage.summary_file, 'r') as f:
            report_data = json.load(f)
            self.assertEqual(report_data['total_places_found'], 100)

if __name__ == '__main__':
    unittest.main()
