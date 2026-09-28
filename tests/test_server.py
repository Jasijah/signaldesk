"""Exercise actual HTTP routes and persistent state changes."""
import json
import os
from unittest.mock import patch
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
        with patch.dict(os.environ, {"SIGNALDESK_ALLOW_RESET": "1"}):
            self.call("/api/reset", {})

    def call(self, route, data=None):
        payload = None if data is None else json.dumps(data).encode()
        request = Request(self.base + route, data=payload, headers={"Content-Type":"application/json", "X-SignalDesk-Token": app.WRITE_TOKEN})
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
        with patch.dict(os.environ, {"SIGNALDESK_ALLOW_RESET": "1"}):
            self.call("/api/reset", {})
        self.assertEqual(self.call("/api/business")["name"], "Your business")

    def test_writes_require_token_and_reset_opt_in(self):
        with self.assertRaises(HTTPError) as denied:
            urlopen(Request(self.base + "/api/cases", data=b"{}", headers={"Content-Type":"application/json"}))
        self.assertEqual(denied.exception.code, 401)
        with self.assertRaises(HTTPError) as denied:
            self.call("/api/reset", {})
        self.assertEqual(denied.exception.code, 403)


class PilotApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db, self.old_pilot = app.DB, app.PILOT
        app.DB = Path(self.temp.name) / "pilot.sqlite3"
        app.PILOT = True
        app.INTAKE_LIMIT.clear()
        app.initialize()
        self.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.DB, app.PILOT = self.old_db, self.old_pilot
        self.temp.cleanup()

    def request(self, route, data=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-SignalDesk-Token"] = token
        request = Request(self.base + route, data=None if data is None else json.dumps(data).encode(), headers=headers)
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_private_cases_and_public_customer_submission(self):
        with self.assertRaises(HTTPError) as denied:
            self.request("/api/cases")
        self.assertEqual(denied.exception.code, 401)
        self.assertEqual(self.request("/api/cases", token=app.WRITE_TOKEN), [])
        payload = {"account": "Test Customer", "email": "test@example.com", "subject": "Appointment question",
                   "issue": "Please confirm my appointment", "category": "Appointment", "channel": "SMS",
                   "payment": "Owner verified paid"}
        created = self.request("/api/public/intake", payload)
        self.assertEqual(set(created), {"id"})
        case = self.request("/api/cases/" + created["id"], token=app.WRITE_TOKEN)
        self.assertEqual(case["channel"], "Private form")
        self.assertNotIn("owner verified paid", case["tags"])
        self.assertIn("test@example.com", case["notes"][0]["body"])
        with self.assertRaises(HTTPError) as denied:
            self.request("/api/cases/" + created["id"])
        self.assertEqual(denied.exception.code, 401)
        with self.assertRaises(HTTPError) as denied:
            self.request("/api/reset", {}, token=app.WRITE_TOKEN)
        self.assertEqual(denied.exception.code, 403)

    def test_bad_email_rejected_and_public_rate_limited(self):
        payload = {"account": "Test Customer", "email": "invalid", "subject": "Appointment question",
                   "issue": "Please confirm my appointment", "category": "Appointment"}
        with self.assertRaises(HTTPError) as denied:
            self.request("/api/public/intake", payload)
        self.assertEqual(denied.exception.code, 400)
        payload["email"] = "test@example.com"
        for _ in range(9):
            self.request("/api/public/intake", payload)
        with self.assertRaises(HTTPError) as denied:
            self.request("/api/public/intake", payload)
        self.assertEqual(denied.exception.code, 429)


if __name__ == "__main__":
    unittest.main()
