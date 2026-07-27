"""JSON meetings endpoint — powers the in-page calendar view."""

from typing import Any

from fastapi import APIRouter, Query, Request, Response

from ..meeting_query import filter_by_committee, load_meetings

router = APIRouter(prefix="/api")

# Browsers may reuse a response this long; the server-side TTL cache still
# governs how often we actually call Congress.gov.
_BROWSER_CACHE_SECONDS = 300


@router.get("/meetings")
async def meetings_json(
    request: Request,
    response: Response,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    committee: str | None = Query(None, description="Comma-separated committee systemCodes"),
    congress: int | None = Query(None, ge=1, le=200),
    days_ahead: int | None = Query(None, ge=0, le=365),
    days_behind: int | None = Query(None, ge=0, le=365),
) -> dict[str, Any]:
    """Return committee meetings as JSON, sorted earliest first."""
    window = await load_meetings(
        request,
        chamber=chamber,
        congress=congress,
        days_ahead=days_ahead,
        days_behind=days_behind,
    )

    meetings = window.meetings
    if committee:
        meetings = filter_by_committee(meetings, committee)

    meetings = sorted(meetings, key=lambda m: m.date)

    response.headers["Cache-Control"] = f"public, max-age={_BROWSER_CACHE_SECONDS}"
    return {
        "congress": window.congress,
        "from_date": window.from_date,
        "to_date": window.to_date,
        "count": len(meetings),
        "meetings": [m.to_summary_dict() for m in meetings],
    }
