import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from simulation import simulation_service
from simulation.events import make_event, sse_encode


class SimulationServiceTests(unittest.TestCase):
    def test_invalid_coordinates_are_rejected(self):
        with self.assertRaises(simulation_service.SimulationError):
            simulation_service.create_simulation({"latitude": 91, "longitude": 78})

    def test_simulation_has_explainable_risk_and_geojson(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(simulation_service, "ARCHIVE_DIR", Path(directory)):
                state = simulation_service.create_simulation({
                    "latitude": 30.1472,
                    "longitude": 78.5925,
                    "duration_minutes": 30,
                    "time_step_minutes": 15,
                })
                self.assertEqual(state["status"], "CREATED")
                self.assertEqual(state["risk_map"]["type"], "FeatureCollection")
                self.assertEqual(len(state["timeline"]), 3)
                self.assertEqual(set(state["risk"]["contributors"]), set(simulation_service.RISK_WEIGHTS))
                self.assertEqual(simulation_service.get_simulation(state["simulation_id"])["simulation_id"], state["simulation_id"])

    def test_missing_firms_cache_is_marked_as_simulation_input(self):
        with patch.object(simulation_service, "FIRMS_CACHE_DIR", Path("missing-test-cache")):
            points, source = simulation_service._load_firms("missing", 30, 78)
        self.assertEqual(len(points), 1)
        self.assertEqual(source["kind"], "simulation_input")

    def test_written_archive_is_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(simulation_service, "ARCHIVE_DIR", Path(directory)):
                state = simulation_service.create_simulation({"latitude": 30, "longitude": 78})
                archive = Path(directory) / f"{state['simulation_id']}.json"
                self.assertEqual(json.loads(archive.read_text())["simulation_id"], state["simulation_id"])

    def test_event_envelope_is_sse_compatible(self):
        event = make_event("sim_test", "COMPLETED", "simulation.completed", "2026-09-27T00:00:00Z")
        encoded = "".join(sse_encode([event]))
        self.assertIn("event: simulation.completed", encoded)
        self.assertIn('"simulation_id":"sim_test"', encoded)


if __name__ == "__main__":
    unittest.main()