# Corner Store Scanner

This project is a data collection system for gathering convenience store data from the Google Places API. It uses an adaptive, multi-stage grid scanning method to efficiently scan a large circular area while minimizing API costs.

## Features

- **Adaptive Grid Scanning**: A three-stage scanning process (macro, fine, enhanced) to focus on high-density areas.
- **Cost-Efficiency**: Avoids unnecessary API calls in low-density areas and uses boundary optimization to stay within the target area.
- **Resilience**: Supports session management to resume interrupted scans.
- **Configurability**: All scanning parameters, API keys, and budget limits are configurable.

## Architecture

The system is composed of the following key components:

- **`main.py` (MainScanner)**: The main entry point and orchestrator.
- **`config.py` (ScanConfig)**: Holds all configurable parameters.
- **`grid_generator.py` (GridGenerator)**: Generates the grid points for each scanning stage.
- **`places_client.py` (PlacesAPIClient)**: A client for interacting with the Google Places API.
- **`file_storage.py` (LocalFileStorage)**: Manages all disk I/O.
- **`session_manager.py` (ScanSessionManager)**: Handles the lifecycle of a scan session.
- **`progress_monitor.py` (SimpleProgressMonitor)**: Provides real-time console feedback.

## Usage

### Prerequisites

- Python 3.10+
- An environment variable named `GOOGLE_PLACES_API_KEY` set to your Google Places API key.

### Running a Scan

To start a new scan, you must provide the center coordinates and the radius of the scan area.

```bash
python -m corner_store_scanner.main --run --center "34.0522,-118.2437" --radius 50
```

**Command-line Arguments:**

- `--run`: Start a new scan. This is the default action.
- `--center <lat,lon>`: **(Required)** The center coordinates for the scan area.
- `--radius <km>`: **(Required)** The total scan radius in kilometers.
- `--budget <usd>`: The maximum budget for API calls in USD (overrides the default in `config.py`).
- `--macro-spacing <km>`: The spacing for the macro grid in kilometers (overrides the default).

### Session Management

- **List available sessions:**
  ```bash
  python -m corner_store_scanner.main --list-sessions
  ```

- **Resume a specific session:**
  ```bash
  python -m corner_store_scanner.main --resume <SCAN_ID>
  ```

- **Clean up completed sessions:**
  ```bash
  python -m corner_store_scanner.main --cleanup-sessions
  ```

## Development and Testing

### Setting up the Environment

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd corner-store-scanner
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set the API Key:**
    ```bash
    export GOOGLE_PLACES_API_KEY="your_api_key_here"
    ```

### Running Tests

To run the full test suite:

```bash
python -m unittest discover -s corner_store_scanner/tests
```
