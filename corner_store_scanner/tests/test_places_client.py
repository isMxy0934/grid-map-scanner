import unittest
import os
from unittest.mock import patch
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.places_client import PlacesAPIClient
from corner_store_scanner.models import Coordinate

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

if __name__ == '__main__':
    unittest.main()
