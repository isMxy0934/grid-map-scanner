import os
import json
import csv
from typing import List, Set, Dict
from datetime import datetime

from .models import PlaceData, GridPoint
from .config import ScanConfig

class LocalFileStorage:
    """
    Handles all disk I/O for saving scan results and progress.
    """
    def __init__(self, config: ScanConfig, session_id: str):
        """
        Initializes the LocalFileStorage.

        Args:
            config: The ScanConfig instance.
            session_id: The unique identifier for the current scan session.
        """
        self.config = config
        self.session_id = session_id
        
        # Define base data directory
        self.data_dir = "data"
        
        # Define session-specific directory
        self.session_dir = os.path.join(self.data_dir, self.session_id)
        
        # Define file paths
        self.places_file = os.path.join(self.session_dir, "places_results.csv")
        self.progress_file = os.path.join(self.session_dir, "progress.json")
        self.failed_log_file = os.path.join(self.session_dir, "failed.log")
        self.summary_file = os.path.join(self.session_dir, "scan_summary.json")

        self.ensure_data_directories()

    def ensure_data_directories(self):
        """
        Ensures that the base data directory and session-specific directory exist.
        """
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.session_dir, exist_ok=True)

    def save_places(self, places: List[PlaceData]):
        """
        Saves a list of PlaceData objects to the CSV file.
        Appends to the file if it already exists.
        """
        # Check if the file exists to write headers
        file_exists = os.path.isfile(self.places_file)
        
        with open(self.places_file, 'a', newline='', encoding='utf-8') as f:
            if not places:
                return
            # Use the first place's dict keys for header
            writer = csv.DictWriter(f, fieldnames=places[0].to_csv_row().keys())
            if not file_exists:
                writer.writeheader()
            for place in places:
                writer.writerow(place.to_csv_row())

    def save_progress(self, grid_point_id: str):
        """
        Records a completed grid point ID. This is a simple append-only log
        for resuming, not a sophisticated state management system.
        """
        with open(self.progress_file, 'a', encoding='utf-8') as f:
            f.write(f"{grid_point_id}\n")

    def log_failed_point(self, grid_point: GridPoint, error: str):
        """
        Logs the ID of a grid point that failed all retry attempts.
        """
        with open(self.failed_log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()}: {grid_point.id} - {error}\n")

    def load_progress(self) -> Set[str]:
        """
        Loads the set of completed grid point IDs from the progress file.

        Returns:
            A set of strings, where each string is a completed grid point ID.
            Returns an empty set if the progress file does not exist.
        """
        if not os.path.isfile(self.progress_file):
            return set()
        
        with open(self.progress_file, 'r', encoding='utf-8') as f:
            # Read lines and strip newlines
            return {line.strip() for line in f if line.strip()}

    def generate_summary_report(self) -> Dict[str, any]:
        """
        Generates a summary report of the scan and saves it to a file.

        Returns:
            A dictionary containing the summary data.
        """
        total_places = 0
        if os.path.isfile(self.places_file):
            with open(self.places_file, 'r', encoding='utf-8') as f:
                # Subtract 1 for the header row
                total_places = max(0, sum(1 for row in f) - 1)
        
        failed_points = 0
        if os.path.isfile(self.failed_log_file):
            with open(self.failed_log_file, 'r', encoding='utf-8') as f:
                failed_points = sum(1 for row in f)

        summary = {
            "session_id": self.session_id,
            "scan_end_time": datetime.now().isoformat(),
            "total_places_found": total_places,
            "failed_grid_points": failed_points,
            "results_file": self.places_file,
            "progress_file": self.progress_file,
            "failed_log_file": self.failed_log_file
        }

        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)
            
        return summary
