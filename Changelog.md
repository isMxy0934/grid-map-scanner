## 2025-07-18
- Added tests for `ScanResult` to cover `to_dict` and `from_dict` round-trip behavior.

## 2025-07-17
- Added `requests` dependency in `pyproject.toml` to ensure tests can import the HTTP library.
- Removed redundant `session_dir` patches in `test_integration.py`.
- Updated README to install with `pip install .` and mention `uv`.
