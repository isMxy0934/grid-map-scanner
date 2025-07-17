import os
import requests
import time
from datetime import datetime
from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import GridPoint
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

    def _make_api_request(self, center: Coordinate, radius: int) -> requests.Response:
        """
        Makes the actual HTTP POST request to the Google Places API.

        Args:
            center: The center coordinate for the search.
            radius: The search radius in meters.

        Returns:
            The Response object from the requests library.
        """
        headers = self._prepare_headers()
        payload = self._prepare_payload(center, radius)
        response = requests.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=self.config.API_TIMEOUT
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response

    def _extract_places(self, response_data: dict, grid_point_id: str, scan_level: int) -> List[PlaceData]:
        """
        Extracts and transforms place data from the API response.

        Args:
            response_data: The JSON response data from the API.
            grid_point_id: The ID of the grid point that this search originated from.
            scan_level: The scan level of the search.

        Returns:
            A list of PlaceData objects.
        """
        places = response_data.get('places', [])
        extracted_data = []
        for place in places:
            # Safely get nested dictionary values
            postal_address = place.get('postalAddress', {})
            location = place.get('location', {})

            extracted_data.append(
                PlaceData(
                    place_id=place.get('id'),
                    name=place.get('name'),
                    formatted_address=place.get('formattedAddress'),
                    latitude=location.get('latitude'),
                    longitude=location.get('longitude'),
                    postal_address=f"{postal_address.get('addressLines', [])}, {postal_address.get('postalCode', '')}, {postal_address.get('locality', '')}",
                    types=place.get('types', []),
                    photos=[photo.get('name', '') for photo in place.get('photos', [])],
                    grid_point_id=grid_point_id,
                    scan_time=datetime.now().isoformat(),
                    scan_level=scan_level
                )
            )
        return extracted_data

    def nearby_search(self, grid_point: "GridPoint") -> Optional[List[PlaceData]]:
        """
        Executes a Nearby Search API call for a given grid point with retry logic.

        Args:
            grid_point: The GridPoint to search around.

        Returns:
            A list of PlaceData objects if successful, otherwise None.
        """
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = self._make_api_request(grid_point.center, grid_point.radius)
                return self._extract_places(response.json(), grid_point.id, grid_point.level)
            except requests.exceptions.RequestException as e:
                print(f"API request failed (attempt {attempt + 1}/{self.config.MAX_RETRIES}): {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY * (2 ** attempt)) # Exponential backoff
                else:
                    return None # All retries failed
            except Exception as e:
                print(f"An unexpected error occurred during API call (attempt {attempt + 1}): {e}")
                return None
        return None
