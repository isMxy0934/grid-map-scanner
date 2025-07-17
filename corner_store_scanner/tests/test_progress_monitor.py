import unittest
from unittest.mock import patch, MagicMock
import time
from datetime import datetime, timedelta

from corner_store_scanner.config import ScanConfig
from corner_store_scanner.progress_monitor import SimpleProgressMonitor

class TestSimpleProgressMonitor(unittest.TestCase):

    def setUp(self):
        self.config = ScanConfig()
        self.config.API_COST_PER_CALL = 0.05
        self.config.MAX_BUDGET = 10.0
        self.monitor = SimpleProgressMonitor(self.config, total_grid_points=100, session_id="test_session")

    def test_initialization(self):
        self.assertEqual(self.monitor.total_grid_points, 100)
        self.assertEqual(self.monitor.completed_count, 0)
        self.assertEqual(self.monitor.api_call_count, 0)
        self.assertEqual(self.monitor.current_cost, 0.0)
        self.assertEqual(self.monitor.session_id, "test_session")

    def test_update_progress_and_cost(self):
        self.monitor.update_progress(completed_grid_points=10, api_calls_made=50)
        self.assertEqual(self.monitor.completed_count, 10)
        self.assertEqual(self.monitor.api_call_count, 50)
        self.assertAlmostEqual(self.monitor.current_cost, 2.5) # 50 * 0.05

    @patch('corner_store_scanner.progress_monitor.logger')
    def test_print_progress_throttling(self, mock_logger):
        self.monitor.last_print_time = time.time()
        
        # First call should not print as not enough time has passed
        self.monitor.print_progress()
        mock_logger.info.assert_not_called()
        
        # Move time forward to trigger print
        self.monitor.last_print_time = time.time() - 10
        self.monitor.print_progress()
        mock_logger.info.assert_called_once()
        
    @patch('corner_store_scanner.progress_monitor.logger')
    def test_print_progress_final_update(self, mock_logger):
        self.monitor.completed_count = 100 # Match total_grid_points
        self.monitor.print_progress()
        mock_logger.info.assert_called_once()
        self.assertIn("Progress: 100.00%", mock_logger.info.call_args[0][0])
        
    @patch('corner_store_scanner.progress_monitor.logger')
    def test_check_budget_exceeded(self, mock_logger):
        # Set cost above budget
        self.monitor.current_cost = 15.0
        self.monitor.check_budget()
        mock_logger.warning.assert_called_once()
        self.assertIn("Budget limit ($10.00) exceeded", mock_logger.warning.call_args[0][0])
        
    @patch('corner_store_scanner.progress_monitor.logger')
    def test_check_budget_not_exceeded(self, mock_logger):
        self.monitor.current_cost = 5.0
        self.monitor.check_budget()
        mock_logger.warning.assert_not_called()
        
    @patch('corner_store_scanner.progress_monitor.logger')
    def test_print_final_summary(self, mock_logger):
        self.monitor.api_call_count = 200
        self.monitor.current_cost = 10.0
        self.monitor.print_final_summary(total_places_found=150, failed_grid_points=5)
        
        # Final summary should have 7 info calls + 1 for the newline
        self.assertEqual(mock_logger.info.call_count, 8)
        
        # Check some key parts of the summary
        log_calls = " ".join([call[0][0] for call in mock_logger.info.call_args_list])
        self.assertIn("--- Scan Summary ---", log_calls)
        self.assertIn("Total Places Found: 150", log_calls)
        self.assertIn("Final Cost: $10.00", log_calls)
        self.assertIn("Failed Grid Points: 5", log_calls)

if __name__ == '__main__':
    unittest.main()
