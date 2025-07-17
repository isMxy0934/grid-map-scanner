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
