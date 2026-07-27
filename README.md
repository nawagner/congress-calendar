# Congress Committee Meeting Calendar

Browsable and subscribable calendar of U.S. Congress committee meetings. Built with FastAPI, powered by the [Congress.gov API](https://api.congress.gov/).

The web UI shows what Congress has scheduled right away — no setup required. Toggling chambers and committees filters the agenda instantly, and the subscribe buttons hand Apple Calendar, Google Calendar, or Outlook a feed of exactly what's on screen.

## Quick Start

```bash
# Clone and install
git clone https://github.com/nawagner/congress-calendar.git
cd congress-calendar
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env and add your Congress.gov API key
# Get one at https://api.congress.gov/sign-up/

# Run
python -m congress_calendar
```

The server starts at `http://localhost:8000`.

## Endpoints

| Path | Description |
|------|-------------|
| `/` | Web UI — browse the calendar, toggle committees, subscribe |
| `/calendar/meetings.ics` | iCal feed (see query params below) |
| `/api/meetings` | Same meetings as JSON; powers the browse view |
| `/health` | Health check |
| `/docs` | OpenAPI documentation |

### Query Parameters

Both `/calendar/meetings.ics` and `/api/meetings` take the same filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chamber` | `house` or `senate` | all | Filter by chamber |
| `committee` | string | all | Comma-separated committee system codes |
| `congress` | int | 119 | Congress number |
| `days_ahead` | 0–365 | 30 | Days into the future |
| `days_behind` | 0–365 | 30 | Days into the past |

A parent committee code (one ending in `00`, like `hssy00`) also matches its
subcommittees.

The landing page accepts the same parameters plus `view=past`, so a filtered
calendar is a shareable link: `/?chamber=senate&committee=ssju00`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONGRESS_API_KEY` | yes | — | Congress.gov API key |
| `BASE_URL` | no | auto-detected | Public URL for generated feed links |
| `CACHE_TTL_MINUTES` | no | 30 | API response cache TTL |

## Deployment

Deployed on [Railway](https://railway.app) via nixpacks. Configuration is in `railway.toml`.

```bash
# Set the required env var in Railway
railway variables set CONGRESS_API_KEY=<your-key>
```

## Development

```bash
# Run tests (test_calendar_feed.py hits the live API and needs a key;
# the rest run offline against stubbed data)
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Architecture

```
src/congress_calendar/
├── app.py              # FastAPI app factory + lifespan
├── config.py           # Pydantic settings from env vars
├── congress_client.py  # Async Congress.gov API client with retry/pagination
├── meeting_query.py    # Shared fetch/cache/parse/filter for both endpoints
├── ical_builder.py     # iCal (RFC 5545) calendar generation
├── cache.py            # In-memory TTL cache for API responses
├── models.py           # CommitteeMeeting + CommitteeInfo models
├── committees.py       # Static committee list for 119th Congress
└── routes/
    ├── landing.py      # Web UI at /
    ├── calendar_feed.py # iCal feed at /calendar/meetings.ics
    ├── meetings_api.py  # JSON meetings at /api/meetings
    └── health.py       # Health check at /health
```

The browse view is plain inline JS in `landing.py`: the page fetches both
chambers once from `/api/meetings`, then chamber and committee toggles filter
in the browser, so they respond instantly and never re-hit Congress.gov. The
toggles drive the `.ics` URL too, which is why the subscribe card always
matches the agenda above it.
