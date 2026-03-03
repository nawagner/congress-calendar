# Congress Calendar

## Browser Testing

Use the `agent-browser` CLI tool for browser testing instead of screencapture or Chrome extension MCP tools.

## Project

- Python 3.12+, FastAPI, deployed on Railway
- Single `pyproject.toml` manages all deps — no separate requirements.txt
- All frontend is inline HTML/CSS/JS in `routes/landing.py` — no build step, no static files
- Committee data in `committees.py` is for the 119th Congress (2025–2027) and will need updating when a new Congress convenes
