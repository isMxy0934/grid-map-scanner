import unittest
from unittest.mock import patch, MagicMock
import os
import requests

from corner_store_scanner.config import ScanConfig
from corner_store_scanner.places_client import PlacesAPIClient
from corner_store_scanner.models import GridPoint, Coordinate, PlaceData

# Set a dummy API key for testing purposes
@patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "test_api_key"})
class TestPlacesAPIClient(unittest.TestCase):

    def setUp(self):
        """Set up a common config and client for tests."""
        self.config = ScanConfig()
        # Patch the environment variable before initializing the client
        self.env_patcher = patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "test_api_key"})
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)
        self.client = PlacesAPIClient(self.config)

    def test_initialization_with_api_key(self):
        """Test that the client initializes correctly with an API key."""
        self.assertEqual(self.client.api_key, "test_api_key")

    def test_initialization_without_api_key(self):
        """Test that the client raises an error if the API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                PlacesAPIClient(self.config)

    @patch('requests.post')
    def test_make_api_request(self, mock_post):
        """Test the API request method."""
        # Configure the mock to return a successful response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"places": []}
        mock_post.return_value = mock_response

        client = PlacesAPIClient(self.config)
        center = Coordinate(latitude=34.0, longitude=-118.0)
        response = client._make_api_request(center, 5000)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()

    def test_extract_places(self):
        """Test the extraction of place data from a mock API response."""
        client = PlacesAPIClient(self.config)
        mock_response_data = {
            "places": [
                {
                    "id": "test_id_1",
                    "name": "Test Store",
                    "formattedAddress": "123 Test St, Test City",
                    "location": {"latitude": 34.0, "longitude": -118.0},
                    "postalAddress": {
                        "addressLines": ["123 Test St"],
                        "postalCode": "12345",
                        "locality": "Test City"
                    },
                    "types": ["convenience_store"],
                    "photos": [{"name": "photo1"}]
                }
            ]
        }
        
        extracted = client._extract_places(mock_response_data, "grid_1", 1)
        self.assertEqual(len(extracted), 1)
        self.assertIsInstance(extracted[0], PlaceData)
        self.assertEqual(extracted[0].place_id, "test_id_1")
        self.assertEqual(extracted[0].scan_level, 1)

    @patch('corner_store_scanner.places_client.requests.post')
    @patch('corner_store_scanner.places_client.time.sleep', return_value=None)
    def test_nearby_search_retry_logic(self, mock_sleep, mock_post):
        """Test that nearby_search retries on failure."""
        # Simulate a sequence of failed responses followed by a success
        mock_post.side_effect = [
            requests.exceptions.RequestException("Test network error"),
            requests.exceptions.RequestException("Test network error"),
            unittest.mock.Mock(status_code=200, json=lambda: {"places": []})
        ]

        client = PlacesAPIClient(self.config)
        # The actual grid point data doesn't matter much for this test
        grid_point = GridPoint(center=Coordinate(0, 0), radius=100, level=1)
        
        result = client.nearby_search(grid_point)

        # It should have called post 3 times (2 fails, 1 success)
        self.assertEqual(mock_post.call_count, 3)
        # It should have slept twice
        self.assertEqual(mock_sleep.call_count, 2)
        # It should eventually succeed
        self.assertIsNotNone(result)

    @patch('corner_store_scanner.places_client.requests.post')
    @patch('corner_store_scanner.places_client.time.sleep', return_value=None)
    def test_nearby_search_all_retries_fail(self, mock_sleep, mock_post):
        """Test that nearby_search returns None after all retries fail."""
        # Simulate only failed responses
        mock_post.side_effect = requests.exceptions.RequestException("Test network error")

        client = PlacesAPIClient(self.config)
        grid_point = GridPoint(center=Coordinate(0, 0), radius=100, level=1)
        
        result = client.nearby_search(grid_point)

        # It should have called post MAX_RETRIES times
        self.assertEqual(mock_post.call_count, self.config.MAX_RETRIES)
        # It should return None
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
