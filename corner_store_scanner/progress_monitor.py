import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Set

from .config import ScanConfig
from .models import GridPoint

# Configure logging for progress monitor
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SimpleProgressMonitor:
    """
    Provides simple, real-time feedback in the console, including progress percentage,
    elapsed time, and current estimated cost. It also enforces the budget limit.
    """

    def __init__(self, config: ScanConfig, total_grid_points: int, session_id: str):
        self.config = config
        self.total_grid_points = total_grid_points
        self.session_id = session_id
        self.start_time = datetime.now()
        self.completed_count = 0
        self.api_call_count = 0
        self.current_cost = 0.0
        self.last_print_time = time.time()

    def update_progress(self, completed_grid_points: int, api_calls_made: int):
        """
        Updates the progress metrics and checks for budget limits.
        """
        self.completed_count = completed_grid_points
        self.api_call_count = api_calls_made
        self.current_cost = self.api_call_count * self.config.API_COST_PER_CALL

        self.print_progress()
        self.check_budget()

    def print_progress(self):
        """
        Prints the current progress to the console.
        """
        elapsed_time = datetime.now() - self.start_time
        progress_percent = (self.completed_count / self.total_grid_points) * 100 if self.total_grid_points > 0 else 0

        # Only print if a certain time has passed or it's the final update
        current_time = time.time()
        if current_time - self.last_print_time > 5 or self.completed_count == self.total_grid_points:
            logger.info(f"Session {self.session_id}: Progress: {progress_percent:.2f}% | "
                        f"Completed: {self.completed_count}/{self.total_grid_points} | "
                        f"API Calls: {self.api_call_count} | "
                        f"Cost: ${self.current_cost:.2f} | "
                        f"Elapsed: {str(elapsed_time).split('.')[0]}")
            self.last_print_time = current_time

    def check_budget(self):
        """
        Checks if the current cost exceeds the maximum budget.
        If so, it logs a warning and could potentially stop the scan.
        """
        if self.current_cost > self.config.MAX_BUDGET:
            logger.warning(f"Budget limit (${self.config.MAX_BUDGET:.2f}) exceeded for session {self.session_id}! Current cost: ${self.current_cost:.2f}")
            # In a real scenario, this might trigger a graceful shutdown

    def print_final_summary(self, total_places_found: int, failed_grid_points: int):
        """
        Prints a final summary of the scan.
        """
        total_duration = datetime.now() - self.start_time
        logger.info("\n--- Scan Summary ---")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Total Places Found: {total_places_found}")
        logger.info(f"Total API Calls: {self.api_call_count}")
        logger.info(f"Final Cost: ${self.current_cost:.2f}")
        logger.info(f"Failed Grid Points: {failed_grid_points}")
        logger.info(f"Total Duration: {str(total_duration).split('.')[0]}")
        logger.info("--------------------")