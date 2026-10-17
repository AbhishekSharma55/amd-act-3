import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest

from fastapi import FastAPI
import httpx

from backend.app.factory import create_factory_router, load_fixture, validate_fixture


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture()

    def test_router_mounts_in_another_app_and_returns_the_unchanged_contract(self):
        app = FastAPI()
        app.include_router(create_factory_router())
        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://factory.test") as client:
                response = await client.get("/api/factory")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), self.fixture)
                self.assertEqual((await client.get("/api/solve")).status_code, 404)

        asyncio.run(exercise())

    def test_missing_duplicate_and_unknown_operations_are_rejected(self):
        for mutate in (
            lambda data: data["committed_schedule"].pop(),
            lambda data: data["committed_schedule"].append(copy.deepcopy(data["committed_schedule"][0])),
            lambda data: data["committed_schedule"][0].update(job="J99"),
        ):
            with self.subTest(mutate=mutate):
                invalid = copy.deepcopy(self.fixture)
                mutate(invalid)
                with self.assertRaises(ValueError):
                    validate_fixture(invalid)

    def test_invalid_clock_minutes_and_reverse_windows_are_rejected(self):
        for value in ("09:99", "24:00", "9:00", None):
            with self.subTest(value=value):
                invalid = copy.deepcopy(self.fixture)
                invalid["committed_schedule"][0]["end"] = value
                with self.assertRaisesRegex(ValueError, "valid HH:MM"):
                    validate_fixture(invalid)
        invalid = copy.deepcopy(self.fixture)
        invalid["shift"]["overtime_until"] = "17:00"
        with self.assertRaisesRegex(ValueError, "start < end"):
            validate_fixture(invalid)

    def test_machine_reference_and_duration_are_validated(self):
        for update in ({"machine": "M99"}, {"machine": ["M3"]}, {"end": "09:01"}, {"op": True}):
            with self.subTest(update=update):
                invalid = copy.deepcopy(self.fixture)
                invalid["committed_schedule"][0].update(update)
                with self.assertRaises(ValueError):
                    validate_fixture(invalid)

    def test_bad_fixture_prevents_router_creation_with_a_readable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-fixture.json"
            path.write_text(json.dumps({"now": "10:00"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid-fixture.json.*factory is required"):
                create_factory_router(path)

    def test_missing_file_fails_at_router_creation(self):
        with self.assertRaisesRegex(ValueError, "Invalid factory fixture"):
            create_factory_router(Path("/nonexistent/rehearsal-factory-fixture.json"))


if __name__ == "__main__":
    unittest.main()
