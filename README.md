# SignalDesk

A mobile-friendly customer inbox and support operations portfolio demo for businesses of different sizes and types: shops, studios, agencies, creators, service providers, and partner operations teams. Organize requests, complaints, order issues, appointments, and billing follow-ups from email, text, chat, and private forms. Fictional scenarios include delivery and music partner incidents, a mobile mechanic complaint, and a retail replacement request. The same case workflow brings together intake, timelines, customer communication, and simple metrics.

**All seeded companies, customers, cases, logs, and metrics in demo mode are fictional.** The repository also has an opt-in, single-business pilot mode with a separate empty database and a working customer request form. Pilot mode is a prototype for controlled testing, not a production support platform.

## Single-business pilot

Run locally with a durable database location and a long, randomly generated workspace key. For example:

```bash
export SIGNALDESK_MODE=pilot
export SIGNALDESK_DB="$PWD/pilot-data/signaldesk.sqlite3"
export SIGNALDESK_WRITE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python server.py
```

Open `/` for the owner workspace, enter the key when prompted, set your business name under **Your brand**, and open `/intake.html` for the customer page. Copy the page URL to share it. Customer form submissions create cases, record a reply email in private notes, and return a case reference. The owner can review cases, add notes, change status, and copy a reply draft for their own email account. Pilot mode does not seed fictional records and cannot reset the database. Keep the database and workspace key backed up separately; the key is never printed in pilot mode.

The owner workspace uses one shared secret, not individual accounts. By default the server binds to `127.0.0.1`. **Do not expose it directly to the internet.** For remote testing, put it behind HTTPS with an authenticated owner access layer, rate limits, and a durable private volume; set `SIGNALDESK_HOST` only for a correctly configured reverse proxy. The customer form has a small per-IP in-process throttle and a honeypot, which do not replace edge protection. The owner must check the workspace manually: the app does not yet send email or text notifications or reply on the customer's behalf. Do not collect sensitive personal, payment-card, or medical information.

To launch a multi-business service, build tenant-specific accounts and request URLs, database isolation, password recovery/MFA, email notifications and replies, opt-out handling for messaging, encrypted backups, retention/deletion, abuse monitoring, accessibility review, and an operational incident process. Integrate email first and validate with five businesses before adding SMS and chat. These items are not implemented by this repo.

## Run locally

Requires Python 3.10+. No packages or API keys are needed.

```bash
python server.py
```

Open `http://127.0.0.1:8765`. For a clean demo, stop the server and delete `.signaldesk.sqlite3`; the next start recreates the sample records.

## Guided demo

1. Select **MetroMart delivery** and inspect the status timeline and trace. The customer sees a stale “picked up” state despite a successful dropoff.
2. Select **Run diagnostics**. The rule engine correlates a completed proof-of-delivery event with a failed partner callback and explains the root cause. Select **Simulate replay** to recover the integration, then copy the customer update.
3. Select **Northstar release**. Its partner rejected a metadata payload while a release was marked delivered internally. Run diagnostics to identify the rejected field. Switch between customer and engineering updates.
4. Select **Avery Brooks** for a mobile mechanic SMS complaint, or **Jordan Lee** for a retail web chat replacement request. The Cash App payment is explicitly unverified. Open **New case** to simulate email, SMS, chat, or social DM intake. Preview the fictional customer request form at `/intake.html` (submission is disabled in demo mode). Add an internal note and mark it resolved.
5. Use **Reset demo** to restore the sample data.
6. Open **Your brand** to set a business name, welcome line, and signature color. Preview the same branding on the customer request page.

## What this demonstrates

- API and webhook troubleshooting with event order, status codes, request IDs, and safe replay semantics.
- Support operations: triage, severity, case ownership, notes, evidence, escalation, and customer updates.
- Product thinking: a short investigation path, readable mobile layout, and clear separation between confirmed evidence and suggested action.
- Everyday business adoption: a shared queue for email, text, chat, and social-origin complaints across retail, creative work, professional services, and solo businesses, with optional manual payment context and a private customer request page. The local demo simulates these channels; it does not connect to providers.
- Python standard-library API, SQLite persistence, server-side input validation, and basic HTTP integration tests.

The diagnostic rules are deterministic and transparent. They do not represent a trained AI model. The product can later accept a classifier, but a high quality investigation workflow stands on its own.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health check |
| `GET /api/metrics` | Live demo counts and summaries |
| `GET /api/business` | Current demo business identity |
| `POST /api/business` | Update name, tagline, accent, and business type |
| `GET /api/cases` | Case list; optional `?q=` and `?domain=` |
| `POST /api/cases` | Simulated email/SMS/chat/social/private-form intake |
| `POST /api/public/intake` | Customer request submission in pilot mode only; returns a case reference |
| `GET /api/cases/{id}` | Case, trace, notes, and diagnosis |
| `POST /api/cases/{id}/diagnose` | Run transparent incident rules |
| `POST /api/cases/{id}/replay` | Simulate an idempotent partner replay |
| `POST /api/cases/{id}/status` | Set `open`, `investigating`, or `resolved` |
| `POST /api/cases/{id}/notes` | Add a short internal note |
| `POST /api/reset` | Recreate the fictional sample dataset when `SIGNALDESK_ALLOW_RESET=1` |

All owner writes require `X-SignalDesk-Token`. Pilot case reads require it too; the public customer intake is the only write exception. Demo mode prints a fresh write token on startup; the browser asks for it on the first edit and keeps it for that tab. Set `SIGNALDESK_WRITE_TOKEN` to supply your own. Reset is disabled by default and must be explicitly enabled with `SIGNALDESK_ALLOW_RESET=1` in demo mode. Keep the server bound to localhost unless a secure reverse proxy is configured.

Replay is a simulation for a portfolio demo; it does not send a real webhook. Demo case reads have no authentication, so bind it to localhost and do not expose it publicly as-is.
The channel selector simulates email/SMS/chat/social intake. Only the pilot customer request form submits directly; it does not connect those external channels. A production service needs dedicated connectors, consent and opt-out handling, identity matching, secure user accounts, and abuse protection. It should never scrape private social messages or claim a Cash App payment is verified from a customer's report.

## Portfolio talking points

“I built SignalDesk to show how I approach high volume partner support. At Roadie, I helped define premier support workflows and staffing needs as enterprise volume grew. At UnitedMasters, I worked in distribution operations. This demo turns those experiences into a product: an investigator can trace an integration failure, document the root cause, and give the customer a useful update.”

## Structure

- `server.py`: HTTP API, SQLite store, diagnostics, and replay simulation.
- `web/`: responsive front end; no build step.
- `tests/test_server.py`: API and state transition checks.
