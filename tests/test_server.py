"""Exercise actual HTTP routes and persistent state changes."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server as app


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        app.DB = Path(cls.temp.name) / "test.sqlite3"
        app.initialize()
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp.cleanup()

    def setUp(self):
        self.call("/api/reset", {})

    def call(self, route, data=None):
        payload = None if data is None else json.dumps(data).encode()
        request = Request(self.base + route, data=payload, headers={"Content-Type":"application/json"})
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_delivery_diagnosis_replay_is_idempotent(self):
        original = self.call("/api/cases/SD-1042")
        self.assertEqual(original["status"], "open")
        self.assertIsNone(original["diagnosis"])
        diagnosed = self.call("/api/cases/SD-1042/diagnose", {})
        self.assertEqual(diagnosed["diagnosis"]["label"], "Partner callback timed out")
        recovered = self.call("/api/cases/SD-1042/replay", {})
        self.assertEqual(recovered["status"], "resolved")
        self.assertEqual(recovered["events"][-1]["code"], "200 OK")
        again = self.call("/api/cases/SD-1042/replay", {})
        self.assertEqual(len(again["events"]), len(recovered["events"]))
        self.assertEqual(self.call("/api/metrics")["critical"], 0)

    def test_music_rejection_and_notes(self):
        case = self.call("/api/cases/SD-1043/diagnose", {})
        self.assertIn("Track 07", case["diagnosis"]["cause"])
        with self.assertRaises(HTTPError) as failure:
            self.call("/api/cases/SD-1043/replay", {})
        self.assertEqual(failure.exception.code, 409)
        case = self.call("/api/cases/SD-1043/notes", {"body":"Awaiting corrected metadata"})
        self.assertEqual(case["notes"][0]["body"], "Awaiting corrected metadata")
        case = self.call("/api/cases/SD-1043/status", {"status":"resolved"})
        self.assertEqual(case["status"], "resolved")

    def test_invalid_input_and_static_path_are_rejected(self):
        for route, body in [("/api/cases/SD-1042/status",{"status":"deleted"}),
                            ("/api/cases/SD-1042/notes",{"body":" "})]:
            with self.assertRaises(HTTPError) as failure:
                self.call(route, body)
            self.assertEqual(failure.exception.code, 400)
        with self.assertRaises(HTTPError) as failure:
            self.call("/server.py")
        self.assertEqual(failure.exception.code, 404)

    def test_general_customer_channel_intake(self):
        case = self.call("/api/cases", {"account":"Avery Brooks", "subject":"Damaged order",
                                        "category":"Order issue", "issue":"The item arrived damaged", "channel":"Social DM",
                                        "payment":"Customer reports paid"})
        self.assertEqual(case["domain"], "General")
        self.assertEqual(case["title"], "Damaged order")
        self.assertIn("order issue", case["tags"])
        self.assertEqual(case["channel"], "Social DM")
        self.assertIn("customer reports paid", case["tags"])
        self.assertEqual(case["events"][0]["source"], "Social DM")
        self.assertEqual(self.call("/api/metrics")["customer"], 3)

    def test_business_branding_and_reset(self):
        b = self.call("/api/business", {"name":"Atlas Auto Care","tagline":"Care that comes to you.",
                                        "accent":"#187e76","industry":"Auto"})
        self.assertEqual(b["name"], "Atlas Auto Care")
        self.assertEqual(self.call("/api/business")["accent"], "#187e76")
        self.call("/api/reset", {})
        self.assertEqual(self.call("/api/business")["name"], "Your business")


if __name__ == "__main__":
    unittest.main()
