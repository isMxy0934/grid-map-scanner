# AGENTS.md

This file provides guidance to AGENTS Code (AGENTS.ai/code) when working with code in this repository.

## Project Overview

The project is a data collection system for gathering convenience store data from the Google Places API. It is designed as a script that runs periodically. The core strategy is an **adaptive, multi-stage grid scanning** method to ensure complete data coverage of a large circular area (e.g., Los Angeles) while minimizing API call costs.

The key principles are:
1.  **Cost-Efficiency**: Avoid unnecessary API calls in low-density areas.
2.  **Data Completeness**: Use a recursive, fine-grained approach in high-density areas to overcome API result limits (20 results per call).
3.  **Simplicity & Reliability**: The system is a straightforward data collection script, not a complex, long-running service.
4.  **Resilience**: The script supports session management to resume interrupted scans.

## Code Architecture

The system is composed of several key components as defined in `specs/design.md`:

-   **`main.py` (MainScanner)**: The main entry point and orchestrator. It manages the overall scanning process, coordinating the different stages and components.
-   **`config.py` (ScanConfig)**: A centralized class holding all configurable parameters, such as grid settings, API keys, budget limits, and recursion rules.
-   **`grid_generator.py` (GridGenerator)**: Responsible for generating the grid points for each scanning stage (macro, fine, enhanced). It includes a crucial **boundary optimization** feature that filters out grid points falling outside the target circular area using the **Haversine distance** formula, saving significant costs.
-   **`places_client.py` (PlacesAPIClient)**: A simple client for interacting with the Google Places API. It handles request formation, simple retry logic with exponential backoff, and response parsing.
-   **`file_storage.py` (LocalFileStorage)**: Manages all disk I/O. It saves scan results to CSV, logs failed grid points, and handles progress tracking by saving completed grid point IDs to a JSON file.
-   **`session_manager.py` (ScanSessionManager)**: Handles the lifecycle of a scan. It creates, saves, loads, and resumes scan sessions. This allows the script to be stopped and restarted without losing progress. Each session has a unique ID and a state file storing progress and configuration.
-   **`progress_monitor.py` (SimpleProgressMonitor)**: Provides simple, real-time feedback in the console, including progress percentage, elapsed time, and current estimated cost. It also enforces the budget limit.

### Core Scanning Strategy

The data collection follows a three-stage adaptive process:

1.  **Macro Scan**: A sparse, wide-radius scan (e.g., 7km spacing, 5km radius) to quickly identify high-density "hotspot" areas. Areas with few results are ignored in subsequent steps.
2.  **Fine Scan**: A denser, smaller-radius scan (e.g., 1.4km spacing, 1km radius) conducted *only* within the hotspots identified in the macro scan.
3.  **Enhanced (Recursive) Scan**: If a fine scan point returns the maximum 20 results (indicating data was likely truncated), this triggers a recursive, even finer-grained scan in that specific spot until all data is retrieved or a maximum recursion depth is reached.

## Project File Structure

The intended file structure is as follows:

```
corner_store_scanner/
├── main.py                 # Main script
├── config.py               # Configuration parameters
├── grid_generator.py       # Grid generation logic
├── places_client.py        # Google Places API client
├── file_storage.py         # File storage logic
├── progress_monitor.py     # Console progress monitoring
├── session_manager.py      # Scan session management
├── data/
│   ├── places_results.csv  # Raw data output
│   ├── progress.json       # Completed grid points for resume
│   ├── failed.log          # Log of failed API calls
│   ├── scan_summary.json   # Final report of a scan
│   └── sessions/           # Directory for saved session states
│       └── scan_YYYYMMDD_HHMMSS.json
├── tests/
│   ├── test_grid.py
│   ├── test_config.py
│   └── test_session.py
└── README.md
```

## Commands & Usage

### Parameter Evaluation

The `evaluator/` directory contains scripts to help determine optimal grid parameters *before* running a costly scan.

```bash
# Run the quick evaluator to test different parameter settings
python evaluator/quick_grid_evaluator.py
```

### Main Scan Execution

The main script (`main.py`) will be driven by command-line arguments.

```bash
# Start a new scan for a 50-mile radius around Los Angeles
python main.py --center "34.0522,-118.2437" --radius 50

# Start a scan with a custom budget and different macro spacing
python main.py --center "34.0522,-118.2437" --radius 50 \
  --budget 100 --macro-spacing 5.0

# Resume a previously interrupted scan using its session ID
python main.py --resume --scan-id "scan_20241217_143022"

# List available, uncompleted sessions
python main.py --list-sessions

# Clean up temporary files from completed sessions
python main.py --cleanup-sessions
```

## Development and Testing

-   **Implementation Plan**: The detailed implementation plan is laid out in `specs/tasks.md`. Refer to this file for the step-by-step development roadmap.
-   **Testing Strategy**:
    1.  **Unit Tests**: Test individual components in isolation (e.g., `GridGenerator`, `Haversine` calculations) without making real API calls.
    2.  **Integration Tests**: Perform small-scale, low-cost runs on a tiny area (e.g., 1 sq km) to validate the end-to-end flow of the three-stage scanning process.
    3.  **Parameter Optimization**: Use the evaluator scripts and small-scale tests to fine-tune grid parameters for the best balance of cost and data completeness.

## Development Workflow

This project follows a structured, three-phase workflow for planning and a separate workflow for implementation. All planning artifacts are stored in the `specs/` directory.

### Phase 1: Requirements Gathering
- **Goal**: Define the feature's requirements collaboratively.
- **Artifact**: `specs/requirements.md`
- **Process**:
  1. Generate an initial set of requirements in EARS format (User Story + Acceptance Criteria).
  2. Iterate on the requirements with the user until they are complete, accurate, and explicitly approved.

### Phase 2: Design
- **Goal**: Create a comprehensive technical design based on the approved requirements.
- **Artifact**: `specs/design.md`
- **Process**:
  1. Conduct any necessary research to inform the design.
  2. Create a detailed design document covering Architecture, Components, Data Models, Error Handling, and a Testing Strategy.
  3. Iterate on the design with the user until it is explicitly approved.

### Phase 3: Implementation Planning
- **Goal**: Break down the design into a checklist of actionable, discrete coding tasks.
- **Artifact**: `specs/tasks.md`
- **Process**:
  1. Convert the design into a series of hierarchical, test-driven coding tasks.
  2. Each task should be a checkbox item that is concrete enough for a coding agent to execute.
  3. Review the task list with the user until it is explicitly approved. This concludes the planning phase.

### Implementation Execution
Once the `tasks.md` is approved, the implementation work begins, following this cycle for each task:

1.  **Check for Uncommitted Changes**: Before starting any new task, run `git status`. If there are any modifications, commit them with a descriptive message to ensure a clean working state.
2.  **Consult the Task List**: Review the implementation plan in `specs/tasks.md` to identify the next pending task. The tasks should be completed in the specified order.
3.  **Implement the Task**: Work on the current task, writing code and tests as required.
4.  **Commit Code Changes**: Once a task is fully implemented and tested, commit the code changes. The commit message should clearly reference the completed task (e.g., "feat: Implement GridGenerator component (Task 2)").
5.  **Update and Commit Task List**: After the code is committed, update `specs/tasks.md` by changing the checkbox for the completed task from `[ ]` to `[x]`. Commit this update with a message like `docs(tasks): Mark task 2.1 as complete`. This ensures the task list always reflects the current state of the codebase.
