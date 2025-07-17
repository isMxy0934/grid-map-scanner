import unittest
import os
import shutil
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.file_storage import LocalFileStorage
from corner_store_scanner.models import PlaceData

class TestFileStorage(unittest.TestCase):

    def setUp(self):
        self.config = ScanConfig()
        self.session_id = "test_session_123"
        self.test_data_dir = "test_data"
        # Override the data_dir for testing purposes
        self.storage = LocalFileStorage(self.config, self.session_id)
        self.storage.data_dir = self.test_data_dir
        self.storage.session_dir = os.path.join(self.test_data_dir, self.session_id)
        
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

if __name__ == '__main__':
    unittest.main()
