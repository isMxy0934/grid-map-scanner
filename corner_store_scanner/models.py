from dataclasses import dataclass, field
from typing import List, Set, Dict
from datetime import datetime

@dataclass
class Coordinate:
    latitude: float
    longitude: float

    def __str__(self):
        return f"{self.latitude},{self.longitude}"

@dataclass
class GridPoint:
    center: Coordinate
    radius: int  # Search radius in meters
    level: int   # Scan level (1=macro, 2=fine, 3+=enhanced)
    id: str = field(init=False)

    def __post_init__(self):
        self.id = f"grid_{self.level}_{self.center.latitude}_{self.center.longitude}"

@dataclass
class Area:
    center: Coordinate
    radius_km: float
    name: str = ""

@dataclass
class PlaceData:
    place_id: str
    name: str
    formatted_address: str
    latitude: float
    longitude: float
    postal_address: str
    types: List[str]
    photos: List[str]
    # Scan metadata
    grid_point_id: str
    scan_time: str
    scan_level: int

    def to_csv_row(self) -> dict:
        return {
            'place_id': self.place_id,
            'name': self.name,
            'formatted_address': self.formatted_address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'postal_address': self.postal_address,
            'types': '|'.join(self.types),
            'photos': '|'.join(self.photos),
            'grid_point_id': self.grid_point_id,
            'scan_time': self.scan_time,
            'scan_level': self.scan_level
        }

@dataclass
class ScanSession:
    session_id: str
    target_area: Area
    config_snapshot: Dict
    created_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    current_phase: str = "macro"
    completed_grid_points: Set[str] = field(default_factory=set)
    hotspot_areas: List[Area] = field(default_factory=list)
    extreme_density_points: List[GridPoint] = field(default_factory=list)
    total_api_calls: int = 0
    current_cost: float = 0.0
    is_completed: bool = False

    def to_dict(self) -> dict:
        # Convert dataclasses and sets to JSON-serializable formats
        return {
            'session_id': self.session_id,
            'target_area': {
                'center': {'latitude': self.target_area.center.latitude, 'longitude': self.target_area.center.longitude},
                'radius_km': self.target_area.radius_km,
                'name': self.target_area.name
            },
            'config_snapshot': self.config_snapshot,
            'created_time': self.created_time,
            'last_updated': self.last_updated,
            'current_phase': self.current_phase,
            'completed_grid_points': list(self.completed_grid_points),
            'hotspot_areas': [{'center': {'latitude': area.center.latitude, 'longitude': area.center.longitude}, 'radius_km': area.radius_km, 'name': area.name} for area in self.hotspot_areas],
            'extreme_density_points': [{'id': point.id, 'center': {'latitude': point.center.latitude, 'longitude': point.center.longitude}, 'radius': point.radius, 'level': point.level} for point in self.extreme_density_points],
            'total_api_calls': self.total_api_calls,
            'current_cost': self.current_cost,
            'is_completed': self.is_completed
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScanSession':
        target_area_data = data['target_area']
        target_area = Area(
            center=Coordinate(**target_area_data['center']),
            radius_km=target_area_data['radius_km'],
            name=target_area_data.get('name', '')
        )

        hotspot_areas = [Area(center=Coordinate(**area['center']), radius_km=area['radius_km'], name=area.get('name', '')) for area in data.get('hotspot_areas', [])]
        extreme_density_points = [GridPoint(center=Coordinate(**point['center']), radius=point['radius'], level=point['level']) for point in data.get('extreme_density_points', [])]


        return cls(
            session_id=data['session_id'],
            target_area=target_area,
            config_snapshot=data['config_snapshot'],
            created_time=data.get('created_time', data.get('start_time')),
            last_updated=data.get('last_updated', data.get('start_time')),
            current_phase=data.get('current_phase', 'macro'),
            completed_grid_points=set(data.get('completed_grid_points', [])),
            hotspot_areas=hotspot_areas,
            extreme_density_points=extreme_density_points,
            total_api_calls=data.get('total_api_calls', 0),
            current_cost=data.get('current_cost', 0.0),
            is_completed=data.get('is_completed', False)
        )


@dataclass
class ScanResult:
    total_places_found: int
    total_api_calls: int
    total_cost: float
    failed_grid_points: int
    scan_duration: str
    session_id: str

    def to_dict(self) -> dict:
        return {
            'total_places_found': self.total_places_found,
            'total_api_calls': self.total_api_calls,
            'total_cost': self.total_cost,
            'failed_grid_points': self.failed_grid_points,
            'scan_duration': self.scan_duration,
            'session_id': self.session_id,
            'cost_per_place': self.total_cost / max(self.total_places_found, 1)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScanResult':
        return cls(
            total_places_found=data['total_places_found'],
            total_api_calls=data['total_api_calls'],
            total_cost=data['total_cost'],
            failed_grid_points=data['failed_grid_points'],
            scan_duration=data['scan_duration'],
            session_id=data['session_id'],
        )
