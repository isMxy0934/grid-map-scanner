import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List

from .config import ScanConfig

class ScanSessionManager:
    """
    Manages scan sessions, including creation, loading, and state persistence.
    """
    sessions_dir = "sessions"

    def __init__(self, config: ScanConfig):
        self.config = config
        self.ensure_sessions_directory()

    def ensure_sessions_directory(self):
        """
        Ensures that the base sessions directory exists.
        """
        os.makedirs(self.sessions_dir, exist_ok=True)

    def generate_session_id(self) -> str:
        """
        Generates a unique session ID based on the current timestamp.
        """
        return f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create_new_session(self, session_id: str) -> Dict[str, Any]:
        """
        Creates a new scan session directory and initializes its state.
        """
        session_path = os.path.join(self.sessions_dir, session_id)
        os.makedirs(session_path, exist_ok=True)
        
        config_dict = self.config.to_dict()
        # Save a snapshot of the current config for this session
        config_snapshot_path = os.path.join(session_path, "config.json")
        with open(config_snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=4)
            
        initial_state = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "config_snapshot": config_dict,
            "target_area": {
                "center": {
                    "latitude": self.config.center_latitude,
                    "longitude": self.config.center_longitude
                },
                "radius_km": self.config.scan_radius_km
            },
            "completed_grid_points": [],
            "hotspot_areas": [],
            "extreme_density_points": [],
            "total_api_calls": 0,
            "total_places_found": 0,
            "current_cost": 0.0,
            "is_completed": False
        }
        self.save_session_state(session_id, initial_state)
        return initial_state

    def save_session_state(self, session_id: str, state: Dict[str, Any]):
        """
        Saves the current state of a scan session to a JSON file.
        """
        session_state_path = os.path.join(self.sessions_dir, session_id, "session_state.json")
        with open(session_state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads the state of a specified scan session.
        """
        session_state_path = os.path.join(self.sessions_dir, session_id, "session_state.json")
        if not os.path.exists(session_state_path):
            return None
        with open(session_state_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_available_sessions(self) -> List[str]:
        """
        Lists all available scan session IDs.
        """
        if not os.path.exists(self.sessions_dir):
            return []
        return [d for d in os.listdir(self.sessions_dir) if os.path.isdir(os.path.join(self.sessions_dir, d))]

    def session_exists(self, session_id: str) -> bool:
        """
        Checks if a session directory exists.
        """
        session_path = os.path.join(self.sessions_dir, session_id)
        return os.path.isdir(session_path)

    def check_config_compatibility(self, session_id: str, current_config: ScanConfig) -> bool:
        """
        Checks if the current configuration is compatible with the saved session config.
        """
        session_path = os.path.join(self.sessions_dir, session_id)
        config_snapshot_path = os.path.join(session_path, "config.json")
        if not os.path.exists(config_snapshot_path):
            return False # No saved config to compare against
        
        with open(config_snapshot_path, 'r', encoding='utf-8') as f:
            saved_config_data = json.load(f)
            # Simple comparison: check if key parameters match.
            # A more robust check might involve hashing or detailed field comparison.
            return (saved_config_data.get("center_latitude") == current_config.center_latitude and
                    saved_config_data.get("center_longitude") == current_config.center_longitude and
                    saved_config_data.get("scan_radius_km") == current_config.scan_radius_km and
                    saved_config_data.get("PLACE_TYPES") == list(current_config.PLACE_TYPES))

    def cleanup_completed_sessions(self):
        """
        Removes directories of completed or failed sessions.
        """
        for session_id in self.list_available_sessions():
            session_state = self.load_session(session_id)
            if session_state and session_state.get("status") in ["completed", "failed"]:
                session_path = os.path.join(self.sessions_dir, session_id)
                shutil.rmtree(session_path)
                print(f"Cleaned up session: {session_id}")
