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

    def _haversine_distance(self, coord1: Coordinate, coord2: Coordinate) -> float:
        """
        Calculates the great-circle distance between two points on the earth (specified in decimal degrees)
        using the Haversine formula.
        
        Args:
            coord1: The first coordinate.
            coord2: The second coordinate.
            
        Returns:
            The distance in kilometers.
        """
        # Earth radius in kilometers
        R = 6371.0
        
        lat1_rad = math.radians(coord1.latitude)
        lon1_rad = math.radians(coord1.longitude)
        lat2_rad = math.radians(coord2.latitude)
        lon2_rad = math.radians(coord2.longitude)
        
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance

    def _filter_grid_by_boundary(self, grid_points: List[GridPoint], target_area: Area) -> List[GridPoint]:
        """
        Filters a list of grid points, keeping only those within the circular target area.
        
        Args:
            grid_points: The list of GridPoint objects to filter.
            target_area: The circular Area defining the boundary.
            
        Returns:
            A new list of GridPoint objects that are within the boundary.
        """
        filtered_points = []
        # Add a buffer to the radius to ensure we don't miss points on the very edge
        effective_radius = target_area.radius_km + self.config.BOUNDARY_BUFFER_KM
        for point in grid_points:
            distance = self._haversine_distance(target_area.center, point.center)
            if distance <= effective_radius:
                filtered_points.append(point)
        return filtered_points

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
