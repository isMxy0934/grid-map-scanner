import unittest
from unittest.mock import MagicMock

from corner_store_scanner.config import ScanConfig
from corner_store_scanner.main_scanner import MainScanner

from corner_store_scanner.models import GridPoint, Coordinate

class TestMainScanner(unittest.TestCase):

    def setUp(self):
        self.config = ScanConfig()
        
        # Create mocks for all the components that MainScanner depends on
        self.mock_grid_generator = MagicMock()
        self.mock_api_client = MagicMock()
        self.mock_file_storage = MagicMock()
        self.mock_progress_monitor = MagicMock()
        
        self.scanner = MainScanner(
            config=self.config,
            session_id="test_session_main",
            grid_generator=self.mock_grid_generator,
            api_client=self.mock_api_client,
            file_storage=self.mock_file_storage,
            progress_monitor=self.mock_progress_monitor
        )

    def test_initialization(self):
        """Test that the MainScanner initializes correctly."""
        self.assertIsNotNone(self.scanner)
        self.assertEqual(self.scanner.session_id, "test_session_main")
        self.assertEqual(len(self.scanner.completed_grid_points), 0)
        self.assertEqual(self.scanner.total_places_found, 0)
        
        # Check that the mocked components were assigned correctly
        self.assertEqual(self.scanner.grid_generator, self.mock_grid_generator)
        self.assertEqual(self.scanner.api_client, self.mock_api_client)
        self.assertEqual(self.scanner.file_storage, self.mock_file_storage)
        self.assertEqual(self.scanner.progress_monitor, self.mock_progress_monitor)

    def test_load_progress(self):
        """Test that progress is loaded correctly from the file storage."""
        # Configure the mock file_storage to return a set of completed grid points
        mock_completed_points = {"grid1", "grid2", "grid3"}
        self.mock_file_storage.load_progress.return_value = mock_completed_points
        
        self.scanner.load_progress()
        
        # Verify that the file_storage's load_progress method was called
        self.mock_file_storage.load_progress.assert_called_once()
        
        # Verify that the scanner's internal state was updated
        self.assertEqual(self.scanner.completed_grid_points, mock_completed_points)

    def test_execute_macro_scan(self):
        """Test the main logic of the macro scan phase."""
        # Setup mock grid points
        mock_point_1 = GridPoint(center=Coordinate(0,0), radius=100, level=1) # id will be grid_1_0_0
        mock_point_2 = GridPoint(center=Coordinate(1,1), radius=100, level=1) # id will be grid_1_1_1
        mock_point_3 = GridPoint(center=Coordinate(2,2), radius=100, level=1) # id will be grid_1_2_2

        self.mock_grid_generator.generate_macro_grid.return_value = [mock_point_1, mock_point_2, mock_point_3]
        
        # Scanner has already completed point 3
        self.scanner.completed_grid_points = {"grid_1_2_2"}

        # Mock API responses
        # Point 1 will be high density
        mock_results_1 = [MagicMock()] * self.config.RECURSION_TRIGGER_COUNT 
        # Point 2 is low density
        mock_results_2 = [MagicMock()] * (self.config.RECURSION_TRIGGER_COUNT - 1) 

        self.mock_api_client.nearby_search.side_effect = [mock_results_1, mock_results_2]

        self.scanner.execute_macro_scan()

        # Verification
        # 1. Check that the grid was generated
        self.mock_grid_generator.generate_macro_grid.assert_called_once()
        
        # 2. Check that API client was called for the two non-completed points
        self.assertEqual(self.mock_api_client.nearby_search.call_count, 2)
        self.mock_api_client.nearby_search.assert_any_call(mock_point_1)
        self.mock_api_client.nearby_search.assert_any_call(mock_point_2)
        
        # 3. Check that results were saved for both successful scans
        self.assertEqual(self.mock_file_storage.save_places.call_count, 2)
        
        # 4. Check that progress was saved for both successful scans
        self.assertEqual(self.mock_file_storage.save_progress.call_count, 2)
        self.mock_file_storage.save_progress.assert_any_call("grid_1_0_0")
        self.mock_file_storage.save_progress.assert_any_call("grid_1_1_1")
        
        # 5. Check that only the high-density point was added to the fine grid list
        self.assertEqual(len(self.scanner.high_density_fine_grid_points), 1)
        self.assertEqual(self.scanner.high_density_fine_grid_points[0].id, "grid_1_0_0")

        # 6. Check that the progress monitor was updated
        self.assertEqual(self.mock_progress_monitor.update_progress.call_count, 2)

    def test_execute_enhanced_scan_recursive(self):
        """Test the recursive logic of the enhanced scan phase."""
        # Setup: Assume fine scan identified one extreme-density point
        extreme_density_point = GridPoint(center=Coordinate(20,20), radius=1000, level=2)
        self.scanner.extreme_density_enhanced_grid_points = [extreme_density_point]

        # Mock the grid generator for the enhanced scan
        # Level 3 grid
        enhanced_point_l3 = GridPoint(center=Coordinate(20.01, 20.01), radius=500, level=3)
        # Level 4 grid (will be generated from enhanced_point_l3)
        enhanced_point_l4 = GridPoint(center=Coordinate(20.011, 20.011), radius=250, level=4)
        
        # Grid generator will be called twice: once for level 3, once for level 4
        self.mock_grid_generator.generate_enhanced_grid.side_effect = [
            [enhanced_point_l3], # First call returns one level 3 point
            [enhanced_point_l4]  # Second call returns one level 4 point
        ]
        
        # Mock API responses
        # The L3 point will be high-density, triggering another recursion
        mock_results_l3 = [MagicMock()] * self.config.RECURSION_TRIGGER_COUNT
        # The L4 point will not be high-density, stopping recursion
        mock_results_l4 = [MagicMock()]
        
        self.mock_api_client.nearby_search.side_effect = [mock_results_l3, mock_results_l4]

        # Execute the full scan process, which will trigger the enhanced scan
        self.scanner.run_scan()

        # Verification
        # 1. Check that enhanced grid generator was called twice
        self.assertEqual(self.mock_grid_generator.generate_enhanced_grid.call_count, 2)
        
        # 2. Check API calls for both level 3 and level 4 points
        self.assertEqual(self.mock_api_client.nearby_search.call_count, 2)
        self.mock_api_client.nearby_search.assert_any_call(enhanced_point_l3)
        self.mock_api_client.nearby_search.assert_any_call(enhanced_point_l4)
        
        # 3. Check progress was saved for both points
        self.assertEqual(self.mock_file_storage.save_progress.call_count, 2)


    def test_execute_fine_scan(self):
        """Test the main logic of the fine scan phase."""
        # Setup: Assume macro scan identified one high-density point
        high_density_point = GridPoint(center=Coordinate(10,10), radius=5000, level=1)
        self.scanner.high_density_fine_grid_points = [high_density_point]

        # Mock the grid generator for the fine scan
        fine_point_1 = GridPoint(center=Coordinate(10.1, 10.1), radius=1000, level=2)
        fine_point_2 = GridPoint(center=Coordinate(10.2, 10.2), radius=1000, level=2)
        self.mock_grid_generator.generate_fine_grid.return_value = [fine_point_1, fine_point_2]
        
        # Mock API response for the fine grid points
        self.mock_api_client.nearby_search.return_value = [MagicMock()] 

        self.scanner.execute_fine_scan()

        # Verification
        # 1. Check that the fine grid was generated for the high-density point
        self.mock_grid_generator.generate_fine_grid.assert_called_once_with(high_density_point.center)
        
        # 2. Check that the API was called for each of the new fine grid points
        self.assertEqual(self.mock_api_client.nearby_search.call_count, 2)
        self.mock_api_client.nearby_search.assert_any_call(fine_point_1)
        self.mock_api_client.nearby_search.assert_any_call(fine_point_2)
        
        # 3. Check that progress was saved for each point
        self.assertEqual(self.mock_file_storage.save_progress.call_count, 2)
        
        # 4. Check progress monitor was updated
        self.assertEqual(self.mock_progress_monitor.update_progress.call_count, 2)

    def test_execute_enhanced_scan_recursive(self):
        """Test the recursive logic of the enhanced scan phase."""
        # Setup: Assume fine scan identified one extreme-density point
        extreme_density_point = GridPoint(center=Coordinate(20,20), radius=1000, level=2)
        self.scanner.extreme_density_enhanced_grid_points = [extreme_density_point]

        # Mock the grid generator for the enhanced scan
        # Level 3 grid
        enhanced_point_l3 = GridPoint(center=Coordinate(20.01, 20.01), radius=500, level=3)
        # Level 4 grid (will be generated from enhanced_point_l3)
        enhanced_point_l4 = GridPoint(center=Coordinate(20.011, 20.011), radius=250, level=4)
        
        # Grid generator will be called twice: once for level 3, once for level 4
        self.mock_grid_generator.generate_enhanced_grid.side_effect = [
            [enhanced_point_l3], # First call returns one level 3 point
            [enhanced_point_l4]  # Second call returns one level 4 point
        ]
        
        # Mock API responses
        # The L3 point will be high-density, triggering another recursion
        mock_results_l3 = [MagicMock()] * self.config.RECURSION_TRIGGER_COUNT
        # The L4 point will not be high-density, stopping recursion
        mock_results_l4 = [MagicMock()]
        
        self.mock_api_client.nearby_search.side_effect = [mock_results_l3, mock_results_l4]

        # Execute the full scan process, which will trigger the enhanced scan
        self.scanner.run_scan()

        # Verification
        # 1. Check that enhanced grid generator was called twice
        self.assertEqual(self.mock_grid_generator.generate_enhanced_grid.call_count, 2)
        
        # 2. Check API calls for both level 3 and level 4 points
        self.assertEqual(self.mock_api_client.nearby_search.call_count, 2)
        self.mock_api_client.nearby_search.assert_any_call(enhanced_point_l3)
        self.mock_api_client.nearby_search.assert_any_call(enhanced_point_l4)
        
        # 3. Check progress was saved for both points
        self.assertEqual(self.mock_file_storage.save_progress.call_count, 2)




if __name__ == '__main__':
    unittest.main()
