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
    data_dir = "data"
    session_dir = "sessions"

    def __init__(self, config: ScanConfig, session_id: str):
        """
        Initializes the LocalFileStorage.

        Args:
            config: The ScanConfig instance.
            session_id: The unique identifier for the current scan session.
        """
        self.config = config
        self.session_id = session_id

        # Use class-level defaults so tests can override via patching
        self.data_dir = self.__class__.data_dir

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

    def get_existing_place_ids(self) -> Set[str]:
        """
        Reads the places CSV file and returns a set of all existing place_ids.
        """
        if not os.path.isfile(self.places_file):
            return set()
        
        existing_ids = set()
        with open(self.places_file, 'r', newline='', encoding='utf-8') as f:
            try:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'place_id' in row:
                        existing_ids.add(row['place_id'])
            except (csv.Error, KeyError) as e:
                # Handle empty or malformed CSV
                print(f"Warning: Could not read existing place IDs from {self.places_file}. File might be empty or malformed. Error: {e}")
                return set()
        return existing_ids

    def save_places(self, places: List[PlaceData]):
        """
        Saves a list of new PlaceData objects to the CSV file, avoiding duplicates based on place_id.
        Appends to the file if it already exists.
        """
        if not places:
            return

        existing_place_ids = self.get_existing_place_ids()
        new_places = [p for p in places if p.place_id not in existing_place_ids]

        if not new_places:
            return

        file_exists = os.path.isfile(self.places_file) and os.path.getsize(self.places_file) > 0
        
        with open(self.places_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_places[0].to_csv_row().keys())
            if not file_exists:
                writer.writeheader()
            
            for place in new_places:
                writer.writerow(place.to_csv_row())

    def save_progress(self, grid_point_id: str):
        """
        Records a completed grid point ID to the progress JSON file.
        """
        progress_data = self.load_progress()
        progress_data.add(grid_point_id)
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(list(progress_data), f, indent=4)

    def log_failed_point(self, grid_point: GridPoint, error: str):
        """
        Logs the ID of a grid point that failed all retry attempts.
        """
        with open(self.failed_log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()}: {grid_point.id} - {error}\n")

    def load_progress(self) -> Set[str]:
        """
        Loads the set of completed grid point IDs from the progress JSON file.

        Returns:
            A set of strings, where each string is a completed grid point ID.
            Returns an empty set if the progress file does not exist or is invalid.
        """
        if not os.path.isfile(self.progress_file):
            return set()
        
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
                return set()
        except (json.JSONDecodeError, TypeError):
            # If file is empty, malformed, or not a list, start fresh
            return set()

    def generate_summary_report(self, total_places: int, total_api_calls: int, failed_points: int, scan_duration_seconds: float) -> Dict[str, any]:
        """
        Generates a summary report of the scan and saves it to a file.
        """
        summary = {
            "session_id": self.session_id,
            "scan_end_time": datetime.now().isoformat(),
            "scan_duration_seconds": round(scan_duration_seconds, 2),
            "total_places_found": total_places,
            "total_api_calls": total_api_calls,
            "estimated_cost": total_api_calls * self.config.API_COST_PER_CALL,
            "failed_grid_points": failed_points,
            "results_file": self.places_file,
            "progress_file": self.progress_file,
            "failed_log_file": self.failed_log_file
        }

        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)
            
        return summary
