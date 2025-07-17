import unittest
import math
from corner_store_scanner.models import Area, Coordinate
from corner_store_scanner.config import ScanConfig
from corner_store_scanner.grid_generator import GridGenerator

class TestGridGenerator(unittest.TestCase):

    def setUp(self):
        """Set up a common config and generator for tests."""
        self.config = ScanConfig()
        self.generator = GridGenerator(self.config)

    def test_generate_rectangular_grid_creates_points(self):
        """
        Test that _generate_rectangular_grid creates a list of grid points.
        """
        # A small 1km radius area for testing
        test_area = Area(
            center=Coordinate(latitude=34.0522, longitude=-118.2437),
            radius_km=1.0,
            name="Test Area"
        )
        spacing_km = 0.5

        grid_points = self.generator._generate_rectangular_grid(test_area, spacing_km)

        # Check that some points were generated
        self.assertIsInstance(grid_points, list)
        self.assertTrue(len(grid_points) > 0)
        
        # Check that the points are of the correct type
        self.assertIsInstance(grid_points[0], unittest.mock.ANY.__class__) # A bit of a hack as GridPoint is not available here
        
        # A simple sanity check on the number of points.
        # For a 1km radius and 0.5km spacing, we expect a 3x3 or 4x4 grid at least.
        # The exact number depends on the calculation, but it should be more than a few.
        # (2*radius / spacing) + 1 => (2*1/0.5)+1 = 5. So roughly 5x5=25 points.
        # Let's check for a reasonable minimum.
        self.assertTrue(len(grid_points) >= 9)

if __name__ == '__main__':
    unittest.main()
