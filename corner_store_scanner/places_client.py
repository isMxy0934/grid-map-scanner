import os
import requests
from typing import Optional, List, Dict
from .models import Coordinate, PlaceData
from .config import ScanConfig

class PlacesAPIClient:
    """
    A client for interacting with the Google Places API.
    """
    def __init__(self, config: ScanConfig):
        """
        Initializes the PlacesAPIClient.

        Args:
            config: An instance of ScanConfig containing API parameters.
        
        Raises:
            ValueError: If the GOOGLE_PLACES_API_KEY environment variable is not set.
        """
        self.config = config
        self.api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY environment variable not set.")
        self.base_url = "https://places.googleapis.com/v1/places:searchNearby"

    def _prepare_headers(self) -> Dict[str, str]:
        """Prepares the headers for the API request."""
        return {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': ",".join(self.config.RESPONSE_FIELDS)
        }

    def _prepare_payload(self, center: Coordinate, radius: int) -> Dict:
        """Prepares the JSON payload for the Nearby Search request."""
        return {
            "includedTypes": self.config.PLACE_TYPES,
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": center.latitude,
                        "longitude": center.longitude
                    },
                    "radius": radius
                }
            }
        }
