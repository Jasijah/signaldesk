"""SignalDesk demo API. Standard library only; localhost binding by default."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get("SIGNALDESK_DB", ROOT / ".signaldesk.sqlite3"))
WEB = ROOT / "web"

SEED = [
    {
        "id": "SD-1042", "domain": "Delivery", "account": "MetroMart", "title": "Delivery complete, status still says picked up",
        "subtitle": "Enterprise delivery · Atlanta, GA", "priority": "Critical", "status": "open", "owner": "Premier Support",
        "created": "09:14 AM", "updated": "4 min ago", "sla": "18 min left", "impact": "82 customer orders affected",
        "customer": "Our store teams completed dropoffs, but our order page still says every delivery is in progress. Can you check whether status updates are reaching us?",
        "kind": "callback_timeout", "request_id": "req_7f3c92", "tags": ["webhook", "enterprise", "status sync"],
        "events": [
            ["09:14:02", "Delivery accepted", "dispatch-api", "200 OK", "Order accepted and courier assigned", "success"],
            ["09:31:18", "Pickup scanned", "courier-app", "200 OK", "Pickup state recorded internally", "success"],
            ["10:02:44", "Dropoff verified", "courier-app", "200 OK", "Proof of delivery saved · photo ID pod_441", "success"],
            ["10:02:46", "Partner status callback", "partner-webhook", "504 timeout", "Attempt 1 · destination did not acknowledge in 8s", "error"],
            ["10:04:46", "Automatic retry", "partner-webhook", "504 timeout", "Attempt 2 · same idempotency key ev_881", "error"],
        ],
    },
    {
        "id": "SD-1043", "domain": "Music", "account": "Northstar Records", "title": "Release shows delivered, partner rejected tracks",
        "subtitle": "Catalog delivery · 12 tracks", "priority": "High", "status": "investigating", "owner": "Distribution Ops",
        "created": "08:47 AM", "updated": "12 min ago", "sla": "42 min left", "impact": "1 scheduled release at risk",
        "customer": "We submitted the release yesterday. Your dashboard says delivered, but the streaming partner says there is no valid release in their system.",
        "kind": "metadata_rejection", "request_id": "req_a82de1", "tags": ["partner API", "metadata", "release"],
        "events": [
            ["08:47:11", "Release submitted", "catalog-api", "202 Accepted", "Release submitted to delivery queue", "success"],
            ["08:48:29", "Payload dispatched", "delivery-worker", "200 Sent", "12 tracks sent to Streamline sandbox", "success"],
            ["08:48:34", "Partner validation", "partner-api", "422 Rejected", "Track 07 contributor_role=producer_legacy is unsupported", "error"],
            ["08:48:35", "Dashboard sync", "status-worker", "200 OK", "Internal status reflects dispatch, not partner acceptance", "warning"],
        ],
    },
    {
        "id": "SD-1044", "domain": "Delivery", "account": "Corner Supply", "title": "Duplicate courier assignment after retry",
        "subtitle": "Dispatch integration · Chicago, IL", "priority": "Medium", "status": "open", "owner": "Partner Support",
        "created": "Yesterday", "updated": "23 min ago", "sla": "3h 11m left", "impact": "3 dispatches need review",
        "customer": "We retried a slow create request and now see two couriers on the same order.",
        "kind": "duplicate_request", "request_id": "req_3f28aa", "tags": ["idempotency", "dispatch", "API"],
        "events": [
            ["11:06:02", "Create request", "dispatch-api", "201 Created", "Job created · external_ref CS-203", "success"],
            ["11:06:04", "Client retry", "dispatch-api", "201 Created", "New job created without idempotency key", "warning"],
            ["11:07:39", "Courier assigned", "dispatch-worker", "200 OK", "Two job records now have assignments", "error"],
        ],
    },
    {
        "id": "SD-1045", "domain": "Music", "account": "Harbor Audio", "title": "Catalog update waiting on partner confirmation",
        "subtitle": "Catalog sync · 6 tracks", "priority": "Low", "status": "resolved", "owner": "Distribution Ops",
        "created": "Yesterday", "updated": "Yesterday", "sla": "Met", "impact": "No active listener impact",
        "customer": "Please confirm our metadata update made it to the partner.",
        "kind": "delayed_ack", "request_id": "req_91bb0e", "tags": ["catalog", "acknowledgement"],
        "events": [
            ["14:12:10", "Update submitted", "catalog-api", "202 Accepted", "Update queued", "success"],
            ["14:13:48", "Partner acknowledged", "partner-api", "200 OK", "Acknowledgement received", "success"],
        ],
    },
    {
        "id": "SD-1046", "domain": "Service", "account": "Avery Brooks", "title": "Mobile repair follow-up after a no-start complaint",
        "subtitle": "Mobile mechanic · Atlanta, GA", "priority": "High", "status": "open", "owner": "Owner", "channel": "SMS",
        "created": "Today", "updated": "8 min ago", "sla": "Follow up today", "impact": "1 customer awaiting a callback",
        "customer": "The car started after the visit yesterday, but it will not start this morning. I paid through Cash App. Can you help?",
        "kind": "service_followup", "request_id": "manual_1046", "tags": ["phone intake", "payment reported", "follow-up"],
        "events": [
            ["Yesterday", "Service completed", "owner note", "Logged", "Battery terminal service completed on site; service details are fictional", "success"],
            ["Yesterday", "Payment reported", "manual entry", "Unverified", "Customer reports payment through Cash App; no automatic payment connection", "warning"],
            ["Today", "Complaint received", "business SMS", "Open", "Customer reports the car will not start and asks for help", "error"],
        ],
    },
]

DIAGNOSES = {
    "callback_timeout": {"label": "Partner callback timed out", "confidence": "High confidence · confirmed by trace", "cause": "The dropoff and proof of delivery were recorded internally. Two outbound status callbacks timed out, so the partner never acknowledged the delivered state.", "action": "Replay the failed callback using the original event ID. Confirm a 2xx acknowledgement and ask the partner to verify the order state.", "evidence": ["Proof of delivery pod_441 stored at 10:02:44", "Two 504 callback attempts with idempotency key ev_881", "Internal delivery state is complete"]},
    "metadata_rejection": {"label": "Partner rejected metadata", "confidence": "High confidence · partner response", "cause": "Dispatch succeeded, but the partner returned 422 because Track 07 uses an unsupported contributor role. The dashboard's delivered label refers to dispatch rather than partner acceptance.", "action": "Correct contributor_role for Track 07, resubmit the payload, then wait for partner acceptance before confirming delivery.", "evidence": ["Partner validation returned 422", "Rejected field: contributor_role=producer_legacy", "Dashboard sync used dispatch status"]},
    "duplicate_request": {"label": "Retry created a second job", "confidence": "High confidence · duplicate external reference", "cause": "The partner retried a slow create request without an idempotency key. Both requests created a job and each received a courier assignment.", "action": "Pause further retries, reconcile the two jobs, then add a stable idempotency key to future create requests.", "evidence": ["Two 201 responses for external_ref CS-203", "Second request had no idempotency key", "Two courier assignments recorded"]},
    "delayed_ack": {"label": "Partner acknowledged update", "confidence": "High confidence · partner response", "cause": "The partner accepted the update after a short processing delay. No active incident remains.", "action": "Share the acknowledgement timestamp with the customer.", "evidence": ["Partner returned 200 at 14:13:48"]},
    "service_followup": {"label": "Customer follow-up needed", "confidence": "Intake summary · verify details with customer", "cause": "A customer reported a service issue after a completed visit. The payment is customer-reported and has not been verified against a payment account.", "action": "Reply through the business channel, confirm symptoms and service history, check the payment directly, then agree on a revisit or next step.", "evidence": ["Business SMS complaint logged today", "Prior service noted in owner record", "Payment status is unverified manual entry"]},
    "manual_intake": {"label": "Owner review needed", "confidence": "Demo intake · unverified", "cause": "This case was captured from a customer channel in the demo. No outside inbox or payment system has been checked automatically.", "action": "Review the request, verify any payment in the payment provider, and reply through the business channel with a clear follow-up commitment.", "evidence": ["Customer report captured in inbox", "Service and payment context are demo entries"]},
}


def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def initialize(reset=False):
    with connection() as con:
        if reset:
            con.executescript("DROP TABLE IF EXISTS notes; DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS cases; DROP TABLE IF EXISTS business;")
        con.executescript("""
            CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, domain TEXT, account TEXT, title TEXT, subtitle TEXT,
              priority TEXT, status TEXT, owner TEXT, created TEXT, updated TEXT, sla TEXT, impact TEXT,
              customer TEXT, kind TEXT, request_id TEXT, tags TEXT, channel TEXT DEFAULT 'Partner API', diagnosed INTEGER DEFAULT 0, replayed INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT REFERENCES cases(id),
              time TEXT, title TEXT, source TEXT, code TEXT, detail TEXT, tone TEXT);
            CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT REFERENCES cases(id),
              body TEXT NOT NULL, created TEXT DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS business (id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL,
              tagline TEXT NOT NULL, accent TEXT NOT NULL, industry TEXT NOT NULL);
        """)
        if "channel" not in [r[1] for r in con.execute("PRAGMA table_info(cases)")]:
            con.execute("ALTER TABLE cases ADD COLUMN channel TEXT DEFAULT 'Partner API'")
        con.execute("INSERT OR IGNORE INTO business(id,name,tagline,accent,industry) VALUES (1,'Your business','Thoughtful service, every time.','#3567e9','Services')")
        if con.execute("SELECT count(*) FROM cases").fetchone()[0]:
            return
        for case in SEED:
            con.execute("INSERT INTO cases (id,domain,account,title,subtitle,priority,status,owner,created,updated,sla,impact,customer,kind,request_id,tags) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        tuple(case[k] for k in ("id", "domain", "account", "title", "subtitle", "priority", "status", "owner", "created", "updated", "sla", "impact", "customer", "kind", "request_id")) + (json.dumps(case["tags"]),))
            if case.get("channel"):
                con.execute("UPDATE cases SET channel=? WHERE id=?", (case["channel"], case["id"]))
            con.executemany("INSERT INTO events(case_id,time,title,source,code,detail,tone) VALUES (?,?,?,?,?,?,?)",
                            [(case["id"], *event) for event in case["events"]])


def one_case(con, case_id):
    row = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        return None
    case = dict(row)
    case["tags"] = json.loads(case["tags"])
    case["events"] = [dict(e) for e in con.execute("SELECT time,title,source,code,detail,tone FROM events WHERE case_id=? ORDER BY id", (case_id,))]
    case["notes"] = [dict(n) for n in con.execute("SELECT body,created FROM notes WHERE case_id=? ORDER BY id DESC", (case_id,))]
    case["diagnosis"] = DIAGNOSES[case["kind"]] if case["diagnosed"] else None
    return case


def case_list(q="", domain=""):
    with connection() as con:
        rows = con.execute("SELECT id,domain,account,title,subtitle,priority,status,owner,updated,sla,impact,channel FROM cases ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END").fetchall()
    return [dict(r) for r in rows if (not domain or r["domain"].lower() == domain.lower()) and
            (not q or q.lower() in " ".join(str(v) for v in r).lower())]


def metrics():
    with connection() as con:
        cases = [dict(r) for r in con.execute("SELECT domain,priority,status FROM cases")]
    return {"active": sum(c["status"] != "resolved" for c in cases),
            "critical": sum(c["priority"] == "Critical" and c["status"] != "resolved" for c in cases),
            "resolved": sum(c["status"] == "resolved" for c in cases),
            "delivery": sum(c["domain"] == "Delivery" and c["status"] != "resolved" for c in cases),
            "music": sum(c["domain"] == "Music" and c["status"] != "resolved" for c in cases),
            "service": sum(c["domain"] == "Service" and c["status"] != "resolved" for c in cases)}


def business():
    with connection() as con:
        return dict(con.execute("SELECT name,tagline,accent,industry FROM business WHERE id=1").fetchone())


def save_business(data):
    name, tagline = data.get("name"), data.get("tagline")
    accent, industry = data.get("accent"), data.get("industry")
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 50:
        raise ValueError("Business name must be 2–50 characters")
    if not isinstance(tagline, str) or len(tagline) > 100:
        raise ValueError("Tagline must be 100 characters or fewer")
    if accent not in {"#3567e9", "#885ec7", "#187e76", "#b9744e"}:
        raise ValueError("Choose a supported accent color")
    if industry not in {"Services", "Beauty", "Auto", "Device repair", "Other"}:
        raise ValueError("Choose a supported business type")
    with connection() as con:
        con.execute("UPDATE business SET name=?,tagline=?,accent=?,industry=? WHERE id=1",
                    (name.strip(), tagline.strip(), accent, industry))
    return business()


def create_intake(data):
    account = data.get("account", "")
    service = data.get("service", "")
    issue = data.get("issue", "")
    payment = data.get("payment", "Not discussed")
    channel = data.get("channel", "Email")
    if not all(isinstance(v, str) and 2 <= len(v.strip()) <= 200 for v in (account, service, issue)):
        raise ValueError("Customer, service, and request must each be 2–200 characters")
    if payment not in {"Not discussed", "Unpaid", "Customer reports paid", "Owner verified paid"}:
        raise ValueError("Invalid payment status")
    if channel not in {"Email", "SMS", "Web chat", "Social DM", "Private form", "Phone note"}:
        raise ValueError("Invalid channel")
    with connection() as con:
        seq = con.execute("SELECT COALESCE(MAX(CAST(substr(id,4) AS INTEGER)), 1045)+1 FROM cases").fetchone()[0]
        case_id = f"SD-{seq}"
        values = (case_id, "Service", account.strip(), f"{service.strip()} · customer follow-up", "Solo service · unified inbox",
                  "Medium", "open", "Owner", "Today", "Just now", "Follow up today", "1 customer awaiting a response",
                  issue.strip(), "manual_intake", f"manual_{seq}", json.dumps([channel.lower(), payment.lower()]), channel)
        con.execute("INSERT INTO cases (id,domain,account,title,subtitle,priority,status,owner,created,updated,sla,impact,customer,kind,request_id,tags,channel) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        con.execute("INSERT INTO events(case_id,time,title,source,code,detail,tone) VALUES (?,?,?,?,?,?,?)",
                    (case_id, "Now", "Customer request recorded", channel, "Open", issue.strip(), "warning"))
        con.execute("INSERT INTO events(case_id,time,title,source,code,detail,tone) VALUES (?,?,?,?,?,?,?)",
                    (case_id, "Now", "Payment context recorded", "owner entry", "Unverified" if payment == "Customer reports paid" else "Logged", payment, "warning"))
        return one_case(con, case_id)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path)
        path = route.path
        if path == "/api/health":
            return self.send_json({"ok": True})
        if path == "/api/metrics":
            return self.send_json(metrics())
        if path == "/api/business":
            return self.send_json(business())
        if path == "/api/cases":
            query = parse_qs(route.query)
            return self.send_json(case_list(query.get("q", [""])[0], query.get("domain", [""])[0]))
        if path.startswith("/api/cases/") and path.count("/") == 3:
            with connection() as con:
                case = one_case(con, path.rsplit("/", 1)[-1])
            return self.send_json(case, 200 if case else 404)
        if path == "/":
            path = "/index.html"
        file = (WEB / path.lstrip("/")).resolve()
        if WEB not in file.parents or not file.is_file():
            return self.send_json({"error": "Not found"}, 404)
        mime = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml"}.get(file.suffix, "application/octet-stream")
        content = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 8192:
                return self.send_json({"error": "Request too large"}, 413)
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"error": "Invalid JSON"}, 400)
        if path == "/api/reset":
            initialize(reset=True)
            return self.send_json({"ok": True})
        if path == "/api/business":
            try:
                return self.send_json(save_business(data))
            except ValueError as exc:
                return self.send_json({"error": str(exc)}, 400)
        if path == "/api/cases":
            try:
                return self.send_json(create_intake(data), 201)
            except ValueError as exc:
                return self.send_json({"error": str(exc)}, 400)
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["api", "cases"]:
            return self.send_json({"error": "Not found"}, 404)
        case_id, action = parts[2:]
        with connection() as con:
            case = one_case(con, case_id)
            if not case:
                return self.send_json({"error": "Case not found"}, 404)
            if action == "diagnose":
                con.execute("UPDATE cases SET diagnosed=1,status=CASE WHEN status='open' THEN 'investigating' ELSE status END WHERE id=?", (case_id,))
            elif action == "replay":
                if case["kind"] != "callback_timeout":
                    return self.send_json({"error": "Only the failed callback has a safe replay scenario"}, 409)
                if not case["diagnosed"]:
                    return self.send_json({"error": "Run diagnostics before replay"}, 409)
                if not case["replayed"]:
                    con.execute("INSERT INTO events(case_id,time,title,source,code,detail,tone) VALUES (?,?,?,?,?,?,?)",
                                (case_id, "Now", "Callback replay acknowledged", "partner-webhook", "200 OK", "Simulated replay · original idempotency key ev_881 · partner state updated", "success"))
                    con.execute("UPDATE cases SET replayed=1,status='resolved',updated='Just now' WHERE id=?", (case_id,))
            elif action == "status":
                status = data.get("status")
                if status not in {"open", "investigating", "resolved"}:
                    return self.send_json({"error": "Invalid status"}, 400)
                con.execute("UPDATE cases SET status=?, updated='Just now' WHERE id=?", (status, case_id))
            elif action == "notes":
                note = data.get("body")
                if not isinstance(note, str) or not 1 <= len(note.strip()) <= 500:
                    return self.send_json({"error": "Note must be 1–500 characters"}, 400)
                con.execute("INSERT INTO notes(case_id,body) VALUES (?,?)", (case_id, note.strip()))
            else:
                return self.send_json({"error": "Not found"}, 404)
            return self.send_json(one_case(con, case_id))


if __name__ == "__main__":
    initialize()
    server = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8765"))), Handler)
    print(f"SignalDesk running at http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
