import unittest
import os
from unittest.mock import patch
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.places_client import PlacesAPIClient
from corner_store_scanner.models import Coordinate, PlaceData

class TestPlacesAPIClient(unittest.TestCase):

    def setUp(self):
        self.config = ScanConfig()

    @patch.dict(os.environ, {'GOOGLE_PLACES_API_KEY': 'test_api_key'})
    def test_client_initialization_success(self):
        """Test that the client initializes successfully when the API key is set."""
        client = PlacesAPIClient(self.config)
        self.assertEqual(client.api_key, 'test_api_key')

    @patch.dict(os.environ, {}, clear=True)
    def test_client_initialization_no_api_key(self):
        """Test that the client raises a ValueError if the API key is not set."""
        with self.assertRaises(ValueError):
            PlacesAPIClient(self.config)

    @patch.dict(os.environ, {'GOOGLE_PLACES_API_KEY': 'test_api_key'})
    def test_prepare_headers(self):
        """Test that the request headers are prepared correctly."""
        client = PlacesAPIClient(self.config)
        headers = client._prepare_headers()
        self.assertIn('X-Goog-Api-Key', headers)
        self.assertEqual(headers['X-Goog-Api-Key'], 'test_api_key')
        self.assertIn('X-Goog-FieldMask', headers)
        self.assertIn('places.id', headers['X-Goog-FieldMask'])

    @patch.dict(os.environ, {'GOOGLE_PLACES_API_KEY': 'test_api_key'})
    def test_prepare_payload(self):
        """Test that the request payload is prepared correctly."""
        client = PlacesAPIClient(self.config)
        center = Coordinate(latitude=34.0, longitude=-118.0)
        radius = 5000
        payload = client._prepare_payload(center, radius)
        
        self.assertEqual(payload['locationRestriction']['circle']['center']['latitude'], 34.0)
        self.assertEqual(payload['locationRestriction']['circle']['radius'], 5000)
        self.assertEqual(payload['includedTypes'], self.config.PLACE_TYPES)

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

if __name__ == '__main__':
    unittest.main()
