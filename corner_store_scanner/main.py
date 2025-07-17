import os
import argparse
import logging
from datetime import datetime
from typing import Optional, Set, List

from .config import ScanConfig
from .grid_generator import GridGenerator
from .places_client import PlacesAPIClient
from .file_storage import LocalFileStorage
from .session_manager import ScanSessionManager
from .progress_monitor import SimpleProgressMonitor
from .models import Coordinate, Area, GridPoint, PlaceData, ScanSession, ScanResult

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MainScanner:
    """
    The main orchestrator for the Google Places data collection system.
    Manages the overall scanning process, coordinating different stages and components.
    """

    def __init__(self, config: ScanConfig, session_id: Optional[str] = None):
        self.config = config
        self.session_id = session_id if session_id else ScanSessionManager(config).generate_session_id()
        
        self.session_manager = ScanSessionManager(self.config)
        self.file_storage = LocalFileStorage(self.config, self.session_id)
        self.places_client = PlacesAPIClient(self.config)
        self.grid_generator = GridGenerator(self.config)

        self.current_session: Optional[ScanSession] = None
        self.completed_grid_points: Set[str] = set()
        self.api_call_count: int = 0
        self.total_places_found: int = 0
        self.failed_grid_points_count: int = 0

        # Initialize or load session
        self._initialize_or_load_session()

        # Initialize progress monitor after session is loaded and total_grid_points is known
        # This will be updated after initial grid generation for accurate percentage.
        self.progress_monitor = SimpleProgressMonitor(
            config=self.config,
            total_grid_points=1, # Placeholder, will be updated later
            session_id=self.session_id
        )

    def _initialize_or_load_session(self):
        """
        Initializes a new session or loads an existing one.
        """
        if self.session_manager.session_exists(self.session_id):
            logger.info(f"Attempting to resume session: {self.session_id}")
            loaded_session_data = self.session_manager.load_session(self.session_id)
            if loaded_session_data and self.session_manager.check_config_compatibility(self.session_id, self.config):
                self.current_session = ScanSession.from_dict(loaded_session_data)
                self.completed_grid_points = self.current_session.completed_grid_points
                self.api_call_count = self.current_session.total_api_calls
                self.total_places_found = self.current_session.total_places_found
                logger.info(f"Successfully resumed session {self.session_id} from {self.current_session.last_updated}")
            else:
                logger.warning(f"Cannot resume session {self.session_id}: config incompatible or session data corrupt. Starting new session.")
                self.session_id = self.session_manager.generate_session_id() # Generate new ID
                self.current_session = ScanSession.from_dict(self.session_manager.create_new_session(self.session_id))
        else:
            logger.info(f"Starting new session with ID: {self.session_id}")
            self.current_session = ScanSession.from_dict(self.session_manager.create_new_session(self.session_id))

    def load_progress(self):
        """
        Loads previously completed grid points for resuming a scan.
        This is now handled during _initialize_or_load_session by ScanSessionManager.
        """
        logger.info("Progress loading is handled by ScanSessionManager during session initialization.")

    def execute_macro_scan(self) -> List[Area]:
        """
        Executes the macro scan stage to identify high-density areas.
        """
        logger.info("Starting Macro Scan Stage...")
        
        if self.current_session.current_phase != "created" and self.current_session.hotspot_areas:
             logger.info(f"Macro scan was previously completed. Using {len(self.current_session.hotspot_areas)} stored hotspots.")
             return self.current_session.hotspot_areas

        target_area = Area(center=Coordinate(self.config.center_latitude, self.config.center_longitude),
                           radius_km=self.config.scan_radius_km)
        macro_grid_points = self.grid_generator.generate_macro_grid(
            target_area
        )

        self.progress_monitor.total_grid_points = len(macro_grid_points)
        self.current_session.current_phase = "macro_scan"
        self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())

        hotspot_areas: List[Area] = []

        for i, grid_point in enumerate(macro_grid_points):
            if grid_point.id in self.completed_grid_points:
                logger.info(f"Skipping already completed macro grid point: {grid_point.id}")
                continue

            logger.info(f"Processing macro grid point {i + 1}/{len(macro_grid_points)}: {grid_point.id}")
            
            places, api_calls_made = self.places_client.nearby_search(
                latitude=grid_point.center.latitude,
                longitude=grid_point.center.longitude,
                radius=grid_point.radius,
            )
            self.api_call_count += api_calls_made

            if places:
                for p in places:
                    p.grid_point_id = grid_point.id
                    p.scan_level = grid_point.level
                
                self.file_storage.save_places(places)
                self.total_places_found += len(places)
                logger.info(f"Found {len(places)} places at {grid_point.id}")

                if len(places) >= self.config.RECURSION_TRIGGER_COUNT:
                    hotspot_area = Area(center=grid_point.center, radius_km=grid_point.radius/1000.0)
                    hotspot_areas.append(hotspot_area)
                    logger.info(f"Marked {grid_point.id} as a hotspot for fine scanning.")
            else:
                self.failed_grid_points_count += 1
                self.file_storage.log_failed_point(grid_point, "API returned no places or failed after retries.")

            self.completed_grid_points.add(grid_point.id)
            self.current_session.completed_grid_points = self.completed_grid_points
            self.current_session.total_api_calls = self.api_call_count
            self.current_session.total_places_found = self.total_places_found
            self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())
            self.progress_monitor.update_progress(len(self.completed_grid_points), self.api_call_count)
        
        self.current_session.hotspot_areas = hotspot_areas
        self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())
        logger.info(f"Macro Scan Stage Completed. Identified {len(hotspot_areas)} hotspot areas.")
        return hotspot_areas

    def execute_fine_scan(self, hotspot_areas: List[Area]) -> List[GridPoint]:
        """
        Executes the fine scan stage within the identified hotspot areas.
        """
        logger.info(f"Starting Fine Scan Stage for {len(hotspot_areas)} hotspot areas...")
        if not hotspot_areas:
            logger.info("No hotspot areas to perform fine scan. Skipping.")
            return []

        self.current_session.current_phase = "fine_scan"
        self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())

        all_fine_grid_points = self.grid_generator.generate_fine_grid(hotspot_areas)
        
        logger.info(f"Generated {len(all_fine_grid_points)} fine grid points across all hotspots.")
        
        self.progress_monitor.total_grid_points += len(all_fine_grid_points)

        extreme_density_points: List[GridPoint] = []

        for i, grid_point in enumerate(all_fine_grid_points):
            if grid_point.id in self.completed_grid_points:
                logger.info(f"Skipping already completed fine grid point: {grid_point.id}")
                continue

            logger.info(f"Processing fine grid point {i + 1}/{len(all_fine_grid_points)}: {grid_point.id}")

            places, api_calls_made = self.places_client.nearby_search(
                latitude=grid_point.center.latitude,
                longitude=grid_point.center.longitude,
                radius=grid_point.radius,
            )
            self.api_call_count += api_calls_made

            if places:
                for p in places:
                    p.grid_point_id = grid_point.id
                    p.scan_level = grid_point.level
                
                self.file_storage.save_places(places)
                self.total_places_found += len(places)
                logger.info(f"Found {len(places)} places at fine grid point {grid_point.id}")

                if len(places) >= self.config.RECURSION_TRIGGER_COUNT:
                    extreme_density_points.append(grid_point)
                    logger.info(f"Marked fine grid point {grid_point.id} as extreme density for enhanced scan.")
            else:
                self.failed_grid_points_count += 1
                self.file_storage.log_failed_point(grid_point, "API returned no places or failed after retries.")

            self.completed_grid_points.add(grid_point.id)
            self.current_session.completed_grid_points = self.completed_grid_points
            self.current_session.total_api_calls = self.api_call_count
            self.current_session.total_places_found = self.total_places_found
            self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())
            self.progress_monitor.update_progress(len(self.completed_grid_points), self.api_call_count)

        self.current_session.extreme_density_points = extreme_density_points
        self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())
        logger.info(f"Fine Scan Stage Completed. Identified {len(extreme_density_points)} extreme density points.")
        return extreme_density_points

    def execute_enhanced_scan(self, extreme_density_points: List[GridPoint]):
        """
        Executes the enhanced (recursive) scan for extreme-density points.
        """
        logger.info(f"Starting Enhanced Scan Stage for {len(extreme_density_points)} points...")
        if not extreme_density_points:
            logger.info("No extreme density points to perform enhanced scan. Skipping.")
            return

        self.current_session.current_phase = "enhanced_scan"
        self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())

        for i, point in enumerate(extreme_density_points):
            logger.info(f"Initiating recursive scan for extreme-density point {i + 1}/{len(extreme_density_points)}: {point.id}")
            self._scan_recursively(point, current_depth=1)

    def _scan_recursively(self, grid_point: GridPoint, current_depth: int):
        """
        A private helper method to perform recursive scanning on a given grid point.
        """
        if current_depth > self.config.MAX_RECURSION_DEPTH:
            logger.warning(f"Max recursion depth reached for {grid_point.id}. Halting drill-down.")
            return
        
        if grid_point.radius < self.config.MIN_SEARCH_RADIUS:
             logger.warning(f"Minimum search radius reached for {grid_point.id}. Halting drill-down.")
             return

        logger.info(f"Recursive scan at depth {current_depth} for point {grid_point.id}")

        enhanced_grid = self.grid_generator.generate_enhanced_grid(grid_point)
        
        self.progress_monitor.total_grid_points += len(enhanced_grid)
        
        for i, sub_point in enumerate(enhanced_grid):
            if sub_point.id in self.completed_grid_points:
                logger.info(f"Skipping already completed enhanced grid point: {sub_point.id}")
                continue

            logger.info(f"Processing enhanced grid point {i + 1}/{len(enhanced_grid)} at depth {current_depth}: {sub_point.id}")
            
            places, api_calls_made = self.places_client.nearby_search(
                latitude=sub_point.center.latitude,
                longitude=sub_point.center.longitude,
                radius=sub_point.radius,
            )
            self.api_call_count += api_calls_made

            if places:
                for p in places:
                    p.grid_point_id = sub_point.id
                    p.scan_level = sub_point.level
                
                self.file_storage.save_places(places)
                self.total_places_found += len(places)

                if len(places) >= self.config.RECURSION_TRIGGER_COUNT:
                    logger.info(f"Still encountering high density at {sub_point.id}. Triggering deeper scan.")
                    self._scan_recursively(sub_point, current_depth + 1)
            else:
                self.failed_grid_points_count += 1
                self.file_storage.log_failed_point(sub_point, "API returned no places or failed after retries during enhanced scan.")

            self.completed_grid_points.add(sub_point.id)
            self.current_session.completed_grid_points = self.completed_grid_points
            self.current_session.total_api_calls = self.api_call_count
            self.current_session.total_places_found = self.total_places_found
            self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())
            self.progress_monitor.update_progress(len(self.completed_grid_points), self.api_call_count)


    def run_scan(self):
        """
        Orchestrates the multi-stage scanning process.
        """
        logger.info(f"Starting scan for session: {self.session_id}")
        
        hotspot_areas = self.execute_macro_scan()
        extreme_density_points = self.execute_fine_scan(hotspot_areas)
        self.execute_enhanced_scan(extreme_density_points)

        # Finalize the scan
        self.current_session.is_completed = True
        self.session_manager.save_session_state(self.session_id, self.current_session.to_dict())
        
        # Generate and save summary report
        summary_report = self.file_storage.generate_summary_report(
            total_places=self.total_places_found,
            total_api_calls=self.api_call_count,
            failed_points=self.failed_grid_points_count,
            scan_duration_seconds=(datetime.now() - self.progress_monitor.start_time).total_seconds()
        )
        
        self.progress_monitor.print_final_summary(
            total_places_found=self.total_places_found,
            failed_grid_points=self.failed_grid_points_count
        )
        logger.info(f"Scan session {self.session_id} completed. Summary report saved to {self.file_storage.summary_file}")

def setup_arg_parser() -> argparse.ArgumentParser:
    """
    Sets up the argument parser with all the command-line options.
    """
    parser = argparse.ArgumentParser(
        description="Google Places Data Collection System for Convenience Stores.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Action Commands
    action_group = parser.add_argument_group("Actions")
    action_group.add_argument(
        "--run", 
        action="store_true", 
        help="Start a new scan or resume the latest available session. This is the default action."
    )
    action_group.add_argument(
        "--resume", 
        type=str, 
        metavar="SCAN_ID",
        help="Resume a specific scan session by its ID."
    )
    action_group.add_argument(
        "--list-sessions", 
        action="store_true", 
        help="List all available, uncompleted scan sessions."
    )
    action_group.add_argument(
        "--cleanup-sessions", 
        action="store_true", 
        help="Clean up storage for all completed scan sessions."
    )

    # Scan Parameters (for new scans)
    scan_params_group = parser.add_argument_group("Scan Parameters (for new scans)")
    scan_params_group.add_argument(
        "--center", 
        type=str, 
        help="Center coordinates for the scan area (e.g., \'34.0522,-118.2437\')."
    )
    scan_params_group.add_argument(
        "--radius", 
        type=float, 
        help="Total scan radius in kilometers."
    )
    scan_params_group.add_argument(
        "--budget", 
        type=float, 
        help="Maximum budget for API calls in USD (overrides config)."
    )
    scan_params_group.add_argument(
        "--macro-spacing", 
        type=float, 
        help="Macro grid spacing in kilometers (overrides config)."
    )

    return parser


def handle_list_sessions(manager: ScanSessionManager):
    """
    Lists all available sessions.
    """
    sessions = manager.list_available_sessions()
    if sessions:
        logger.info("Available sessions to resume:")
        for sess_id in sessions:
            logger.info(f"  - {sess_id}")
    else:
        logger.info("No available sessions found.")


def handle_cleanup_sessions(manager: ScanSessionManager):
    """
    Cleans up completed sessions.
    """
    manager.cleanup_completed_sessions()


def run_scan_session(config: ScanConfig, session_id: Optional[str] = None):
    """
    Initializes and runs a scan session.
    """
    scanner = MainScanner(config, session_id=session_id)
    scanner.run_scan()


def main():
    """
    Main entry point for the script.
    Parses command-line arguments and orchestrates the scan.
    """
    parser = setup_arg_parser()
    args = parser.parse_args()

    config = ScanConfig()
    session_manager = ScanSessionManager(config)

    # Handle action commands
    if args.list_sessions:
        handle_list_sessions(session_manager)
    
    elif args.cleanup_sessions:
        handle_cleanup_sessions(session_manager)

    elif args.resume:
        # Resuming a specific session
        logger.info(f"Attempting to resume session: {args.resume}")
        run_scan_session(config, session_id=args.resume)

    else: # Default action: --run or no action specified
        # This block handles starting a new scan or resuming the latest one
        
        # Override config with any provided command-line arguments
        if args.center:
            try:
                lat, lon = map(float, args.center.split(','))
                config.center_latitude = lat
                config.center_longitude = lon
            except (ValueError, IndexError):
                logger.error("Invalid --center format. Please use 'latitude,longitude'.")
                return
        
        if args.radius:
            config.scan_radius_km = args.radius
        
        if args.budget:
            config.MAX_BUDGET = args.budget

        if args.macro_spacing:
            config.MACRO_GRID_SPACING = args.macro_spacing

        # Validate required parameters for a new scan
        if not config.center_latitude or not config.center_longitude or not config.scan_radius_km:
            logger.error("Missing required parameters for a new scan. Please provide --center and --radius.")
            parser.print_help()
            return
            
        logger.info("Starting a new scan with the specified parameters.")
        run_scan_session(config)


if __name__ == '__main__':
    main()
