# Congress Calendar

## Browser Testing

Use the `agent-browser` CLI tool for browser testing instead of screencapture or Chrome extension MCP tools.

## Project

- Python 3.12+, FastAPI, deployed on Railway
- Single `pyproject.toml` manages all deps — no separate requirements.txt
- All frontend is inline HTML/CSS/JS in `routes/landing.py` — no build step, no static files
- The Congress number follows the date (`config.congress_on`), so a new Congress needs no code change. Committee codes in `committees.py` are stable across Congresses, but review its select committees when one convenes (next: the 120th, 2027-01-03)
