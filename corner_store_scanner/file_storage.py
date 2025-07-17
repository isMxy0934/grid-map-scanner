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
