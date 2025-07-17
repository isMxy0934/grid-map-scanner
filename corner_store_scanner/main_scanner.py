from typing import Set, List
from .models import GridPoint

from .config import ScanConfig
from .grid_generator import GridGenerator
from .places_client import PlacesAPIClient
from .file_storage import LocalFileStorage
from .session_manager import ScanSessionManager
from .progress_monitor import SimpleProgressMonitor

class MainScanner:
    """
    Orchestrates the entire scanning process, from grid generation to data storage.
    """

    def __init__(self,
                 config: ScanConfig,
                 session_id: str,
                 grid_generator: GridGenerator,
                 api_client: PlacesAPIClient,
                 file_storage: LocalFileStorage,
                 progress_monitor: SimpleProgressMonitor):
        self.config = config
        self.session_id = session_id
        self.grid_generator = grid_generator
        self.api_client = api_client
        self.file_storage = file_storage
        self.progress_monitor = progress_monitor
        
        # Scan state tracking variables
        self.completed_grid_points: Set[str] = set()
        self.total_places_found = 0
        self.high_density_fine_grid_points: List[GridPoint] = []
        self.extreme_density_enhanced_grid_points: List[GridPoint] = []

    def _process_scan_results(self, grid_point: GridPoint, results: List) -> None:
        """
        Processes the results from a single grid point scan.
        """
        if results is None:
            self.file_storage.log_failed_point(grid_point, "API request failed after all retries.")
            return

        if results:
            self.file_storage.save_places(results)
            self.total_places_found += len(results)

        # Logic to identify high-density areas for the next scan phase
        if len(results) >= self.config.RECURSION_TRIGGER_COUNT:
            if grid_point.level == 1:
                self.high_density_fine_grid_points.append(grid_point)
            elif grid_point.level == 2:
                self.extreme_density_enhanced_grid_points.append(grid_point)
            
        self.file_storage.save_progress(grid_point.id)
        self.completed_grid_points.add(grid_point.id)
        self.progress_monitor.update_progress(
            completed_grid_points=len(self.completed_grid_points),
            api_calls_made=self.progress_monitor.api_call_count + 1
        )

    def execute_macro_scan(self) -> None:
        """
        Executes the initial, broad macro scan.
        """
        macro_grid = self.grid_generator.generate_macro_grid()
        self.progress_monitor.total_grid_points = len(macro_grid)

        for point in macro_grid:
            if point.id in self.completed_grid_points:
                continue
            
            results = self.api_client.nearby_search(point)
            self._process_scan_results(point, results)

    def execute_enhanced_scan(self, points_to_scan: List[GridPoint], current_depth: int):
        """
        Executes a recursive, enhanced scan on extreme-density areas.
        """
        if current_depth > self.config.MAX_RECURSION_DEPTH:
            return
            
        next_level_points = []
        for point in points_to_scan:
            enhanced_grid = self.grid_generator.generate_enhanced_grid(
                point.center, point.radius, point.level
            )
            self.progress_monitor.total_grid_points += len(enhanced_grid)
            
            for enhanced_point in enhanced_grid:
                if enhanced_point.id in self.completed_grid_points:
                    continue
                
                results = self.api_client.nearby_search(enhanced_point)
                self._process_scan_results(enhanced_point, results)
                
                # If this point is still high-density, add for the next recursion level
                if len(results) >= self.config.RECURSION_TRIGGER_COUNT:
                    next_level_points.append(enhanced_point)
        
        if next_level_points:
            self.execute_enhanced_scan(next_level_points, current_depth + 1)


    def execute_fine_scan(self) -> None:
        """
        Executes the second-level fine scan on high-density areas.
        """
        fine_grid_to_scan = []
        for high_density_point in self.high_density_fine_grid_points:
            fine_grid = self.grid_generator.generate_fine_grid(high_density_point.center)
            fine_grid_to_scan.extend(fine_grid)
        
        self.progress_monitor.total_grid_points += len(fine_grid_to_scan)

        for point in fine_grid_to_scan:
            if point.id in self.completed_grid_points:
                continue
            
            results = self.api_client.nearby_search(point)
            self._process_scan_results(point, results)

    def execute_enhanced_scan(self, points_to_scan: List[GridPoint], current_depth: int):
        """
        Executes a recursive, enhanced scan on extreme-density areas.
        """
        if current_depth > self.config.MAX_RECURSION_DEPTH:
            return
            
        next_level_points = []
        for point in points_to_scan:
            enhanced_grid = self.grid_generator.generate_enhanced_grid(
                point.center, point.radius, point.level
            )
            self.progress_monitor.total_grid_points += len(enhanced_grid)
            
            for enhanced_point in enhanced_grid:
                if enhanced_point.id in self.completed_grid_points:
                    continue
                
                results = self.api_client.nearby_search(enhanced_point)
                self._process_scan_results(enhanced_point, results)
                
                # If this point is still high-density, add for the next recursion level
                if len(results) >= self.config.RECURSION_TRIGGER_COUNT:
                    next_level_points.append(enhanced_point)
        
        if next_level_points:
            self.execute_enhanced_scan(next_level_points, current_depth + 1)



    def load_progress(self) -> None:
        """
        Loads the progress from the file storage.
        """
        self.completed_grid_points = self.file_storage.load_progress()
        print(f"Resuming scan. Loaded {len(self.completed_grid_points)} completed grid points.")

    def run_scan(self):
        """
        Executes the full, multi-stage scanning process.
        """
        self.load_progress()
        self.execute_macro_scan()
        self.execute_fine_scan()
        self.execute_enhanced_scan(self.extreme_density_enhanced_grid_points, current_depth=1)
        
        self.progress_monitor.print_final_summary(
            total_places_found=self.total_places_found,
            failed_grid_points=0 # This will be tracked properly later
        )
