import unittest
from corner_store_scanner.models import ScanResult


class TestScanResult(unittest.TestCase):
    def test_to_dict_round_trip(self):
        original = ScanResult(
            total_places_found=5,
            total_api_calls=10,
            total_cost=2.5,
            failed_grid_points=0,
            scan_duration="1s",
            session_id="s1",
        )
        data = original.to_dict()
        new_session = ScanResult.from_dict(data)
        self.assertEqual(new_session.total_places_found, original.total_places_found)
        self.assertEqual(new_session, original)

    def test_from_dict_preserves_total_places_found(self):
        original = ScanResult(
            total_places_found=5,
            total_api_calls=10,
            total_cost=2.5,
            failed_grid_points=0,
            scan_duration="1s",
            session_id="s1",
        )
        data = original.to_dict()
        data["total_places_found"] = 42
        new_result = ScanResult.from_dict(data)
        self.assertEqual(new_result.total_places_found, 42)


if __name__ == "__main__":
    unittest.main()
