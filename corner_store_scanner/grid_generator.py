import math
from typing import List
from .models import Coordinate, Area, GridPoint
from .config import ScanConfig

class GridGenerator:
    def __init__(self, config: ScanConfig):
        """
        Initializes the GridGenerator with a given configuration.

        Args:
            config: An instance of ScanConfig containing all parameters.
        """
        self.config = config

    def _generate_rectangular_grid(self, area: Area, spacing_km: float) -> List[GridPoint]:
        """
        Generates a rectangular grid of points that covers a given circular area.

        This method approximates the conversion from kilometers to degrees for latitude
        and longitude to create a bounding box around the circular area, then populates
        that box with grid points.

        Args:
            area: The circular Area to be covered by the grid.
            spacing_km: The distance between grid points in kilometers.

        Returns:
            A list of GridPoint objects forming the rectangular grid.
        """
        grid_points = []
        
        # Approximate conversion: 1 degree of latitude is roughly 111.1 km
        lat_degree_in_km = 111.1
        
        # Longitude conversion depends on latitude
        lon_degree_in_km = lat_degree_in_km * math.cos(math.radians(area.center.latitude))

        # Calculate the number of grid steps needed to cover the diameter of the circle
        # We add the spacing_km to the radius to ensure full coverage at the edges
        radius_with_buffer = area.radius_km + spacing_km
        
        lat_steps = int(math.ceil(radius_with_buffer / lat_degree_in_km / (spacing_km / lat_degree_in_km)))
        lon_steps = int(math.ceil(radius_with_buffer / lon_degree_in_km / (spacing_km / lon_degree_in_km)))

        for i in range(-lat_steps, lat_steps + 1):
            for j in range(-lon_steps, lon_steps + 1):
                lat_offset = (i * spacing_km) / lat_degree_in_km
                lon_offset = (j * spacing_km) / lon_degree_in_km
                
                point_lat = area.center.latitude + lat_offset
                point_lon = area.center.longitude + lon_offset

                # We will assign a temporary level and radius; these will be set properly
                # in the higher-level methods like generate_macro_grid.
                grid_points.append(GridPoint(
                    center=Coordinate(latitude=point_lat, longitude=point_lon),
                    radius=0, # Placeholder
                    level=0   # Placeholder
                ))
        
        return grid_points
