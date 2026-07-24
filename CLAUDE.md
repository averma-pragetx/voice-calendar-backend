# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # run dev server
ngrok http 8000                              # expose for ElevenLabs webhooks during dev
```

No test suite, linter, or build step configured in this repo.

## Architecture

FastAPI backend bridging an ElevenLabs voice agent to a user's Apple iCloud Calendar via CalDAV. Two request directions:

1. **Outbound trigger** (`app/routers/calls.py`, `POST /calls/trigger`) — this backend calls ElevenLabs' API to place a call, passing `customer_name`/`reason` as dynamic variables the agent's prompt can reference. There's one ElevenLabs agent per calendar provider (`ELEVENLABS_GOOGLE_AGENT_ID`/`ELEVENLABS_APPLE_AGENT_ID` + matching phone number id in `.env`); the request's `provider` field picks which agent/phone number places the call, falling back to `CALENDAR_PROVIDER` if omitted.
2. **Inbound tool webhooks** (`app/routers/tools.py`, `POST /tools/*`) — ElevenLabs calls back into this backend mid-conversation when the agent decides to list/create/update/delete a calendar event. Every route is gated by `verify_webhook_secret`, which checks the `X-Webhook-Secret` header against `TOOL_WEBHOOK_SECRET` — this is the only auth on these endpoints.

`app/calendar_service.py` dispatches every call to whichever backend is active (`settings.calendar_provider`, `"apple"` or `"google"`), so `tools.py` never talks to a provider module directly. Both backends expose the same four functions (`list_events`/`create_event`/`update_event`/`delete_event`):

- `app/caldav_service.py` — Apple iCloud via CalDAV. Module-level `_client`/`_calendar` singletons, lazily initialized and cached across requests. Auth is an app-specific password (Apple 2FA blocks regular password auth for CalDAV). `update_event`/`delete_event` look up the target event via `_find_event_by_uid` — a wide `date_search` (1yr past/2yr future) with manual UID matching, not `calendar.event_by_uid()`, since iCloud's CalDAV server 412s on UID-only queries with no time-range.
- `app/google_calendar_service.py` — Google Calendar API v3. Module-level `_service` singleton. Auth is OAuth2 with a long-lived refresh token (`scripts/google_oauth_setup.py` mints one interactively, one time). `uid` for Google events is the Google event id.

Provider choice is per-request: every tool webhook schema has an optional `provider` field (`"apple"`/`"google"`), passed through to `calendar_service`; if omitted it falls back to `CALENDAR_PROVIDER` in `.env`. This supports running two ElevenLabs agents against one backend, each with its tools configured to send a fixed `provider` value pointing at its own calendar. All datetimes without explicit tz info are assumed to be in `settings.default_timezone` (each service has its own `_parse_dt`).

`app/config.py` defines `Settings` (pydantic-settings), loaded from `.env`. Credentials for both calendar backends live here — one Apple account, one Google account, no per-user credential lookup. `app/schemas.py` holds all request models (tool webhook schemas + the call-trigger schema).

Both routers log every request payload and, on failure, the full exception traceback (`logging.basicConfig` set up in `main.py`) — check the uvicorn console when a live agent call fails, since ElevenLabs only ever hears the agent's generic "having trouble" fallback line.

### Known single-tenant limitation

Each provider (Apple/Google) supports exactly one account, hardcoded in `.env`/`config.py` — not one-account-per-caller. To support multiple end users per provider: replace the Apple/Google credential fields with a DB lookup keyed by `user_id`, and pass `user_id` as a dynamic variable at call-trigger time so ElevenLabs includes it on every tool call back (as a tool parameter or via a `secret__user_id` dynamic variable header).
