# SignalDesk

An interactive portfolio demo for customer support engineering and operations. Investigate fictional partner integration incidents: a last-mile enterprise delivery that stopped sending status updates, and a music release stuck at a distribution partner. A third scenario shows a solo service owner organizing an SMS complaint and a customer-reported payment in a shared business inbox. The product combines intake, event traces, diagnostics, customer communication, and support metrics in a mobile-friendly interface.

**All companies, customers, cases, logs, and metrics in this demo are fictional.** This is a local demo, not a production support platform. It intentionally uses no customer data, AI API, credentials, or external services.

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
4. Select **Avery Brooks** to inspect a mobile mechanic complaint received by business SMS. The Cash App payment is explicitly unverified. Open **New case** to simulate email, SMS, chat, or social DM intake. Preview the fictional customer request form at `/intake.html` to show how a social comment could move into a private case. Add an internal note and mark it resolved.
5. Use **Reset demo** to restore the sample data.
6. Open **Your brand** to set a business name, welcome line, and signature color. Preview the same branding on the customer request page.

## What this demonstrates

- API and webhook troubleshooting with event order, status codes, request IDs, and safe replay semantics.
- Support operations: triage, severity, case ownership, notes, evidence, escalation, and customer updates.
- Product thinking: a short investigation path, readable mobile layout, and clear separation between confirmed evidence and suggested action.
- Small business adoption: one shared queue for email, text, chat, and social-origin complaints, with manual payment context and no need for the owner to use a personal number. The local demo simulates these channels; it does not connect to providers.
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
| `GET /api/cases/{id}` | Case, trace, notes, and diagnosis |
| `POST /api/cases/{id}/diagnose` | Run transparent incident rules |
| `POST /api/cases/{id}/replay` | Simulate an idempotent partner replay |
| `POST /api/cases/{id}/status` | Set `open`, `investigating`, or `resolved` |
| `POST /api/cases/{id}/notes` | Add a short internal note |
| `POST /api/reset` | Recreate the fictional sample dataset |

Replay is a simulation for a portfolio demo; it does not send a real webhook. The demo server has no authentication, so bind it to localhost and do not expose it publicly as-is.
The channel selector also simulates intake. A production service would need dedicated business email/SMS/chat connectors, consent and opt-out handling, identity matching, secure authentication, and a public private-intake form. It should never scrape private social messages or claim a Cash App payment is verified from a customer's report.

## Portfolio talking points

“I built SignalDesk to show how I approach high volume partner support. At Roadie, I helped define premier support workflows and staffing needs as enterprise volume grew. At UnitedMasters, I worked in distribution operations. This demo turns those experiences into a product: an investigator can trace an integration failure, document the root cause, and give the customer a useful update.”

## Structure

- `server.py`: HTTP API, SQLite store, diagnostics, and replay simulation.
- `web/`: responsive front end; no build step.
- `tests/test_server.py`: API and state transition checks.
