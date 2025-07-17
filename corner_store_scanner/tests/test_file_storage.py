import unittest
import os
import shutil
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.file_storage import LocalFileStorage

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

if __name__ == '__main__':
    unittest.main()
