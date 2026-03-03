# Congress Committee Meeting Calendar

Subscribable iCal calendar feed for U.S. Congress committee meetings. Built with FastAPI, powered by the [Congress.gov API](https://api.congress.gov/).

Users visit the web UI to pick chambers and committees, then subscribe in Apple Calendar, Google Calendar, or Outlook with one click.

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
| `/` | Web UI — feed builder with subscribe buttons |
| `/calendar/meetings.ics` | iCal feed (see query params below) |
| `/health` | Health check |
| `/docs` | OpenAPI documentation |

### Feed Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chamber` | `house` or `senate` | all | Filter by chamber |
| `committee` | string | all | Comma-separated committee system codes |
| `congress` | int | 119 | Congress number |
| `days_ahead` | 0–365 | 30 | Days into the future |
| `days_behind` | 0–365 | 30 | Days into the past |

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
# Run tests
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
├── ical_builder.py     # iCal (RFC 5545) calendar generation
├── cache.py            # In-memory TTL cache for API responses
├── models.py           # CommitteeMeeting + CommitteeInfo models
├── committees.py       # Static committee list for 119th Congress
└── routes/
    ├── landing.py      # Web UI at /
    ├── calendar_feed.py # iCal feed at /calendar/meetings.ics
    └── health.py       # Health check at /health
```
