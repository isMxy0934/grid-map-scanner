import unittest
from corner_store_scanner.config import ScanConfig

class TestScanConfig(unittest.TestCase):

    def test_initialization_and_defaults(self):
        config = ScanConfig()
        self.assertEqual(config.MACRO_GRID_SPACING, 7.0)
        self.assertEqual(config.MAX_RECURSION_DEPTH, 3)
        self.assertEqual(config.MAX_BUDGET, 200.0)
        self.assertTrue(config.ENABLE_BOUNDARY_FILTER)
        self.assertEqual(config.center_latitude, 34.0522)
        self.assertIn('convenience_store', config.PLACE_TYPES)
        self.assertIn('places.id', config.RESPONSE_FIELDS)

    def test_custom_initialization(self):
        config = ScanConfig(
            MACRO_GRID_SPACING=10.0,
            MAX_BUDGET=500.0,
            ENABLE_BOUNDARY_FILTER=False
        )
        self.assertEqual(config.MACRO_GRID_SPACING, 10.0)
        self.assertEqual(config.MAX_BUDGET, 500.0)
        self.assertFalse(config.ENABLE_BOUNDARY_FILTER)

    def test_to_dict_method(self):
        config = ScanConfig()
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertIn('MACRO_GRID_SPACING', config_dict)
        self.assertEqual(config_dict['MACRO_GRID_SPACING'], 7.0)
        self.assertIn('PLACE_TYPES', config_dict)
        self.assertIsInstance(config_dict['PLACE_TYPES'], list)
        self.assertEqual(config_dict['PLACE_TYPES'], config.PLACE_TYPES)
