"""Calendar feed endpoint — serves iCal .ics files."""

from fastapi import APIRouter, Query, Request, Response

from ..committees import COMMITTEES_119
from ..ical_builder import build_calendar, calendar_to_bytes
from ..meeting_query import filter_by_committee, load_meetings

router = APIRouter(prefix="/calendar")


@router.get("/meetings.ics")
async def meetings_ics(
    request: Request,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    committee: str | None = Query(None, description="Comma-separated committee systemCodes"),
    congress: int | None = Query(None, ge=1, le=200),
    days_ahead: int | None = Query(None, ge=0, le=365),
    days_behind: int | None = Query(None, ge=0, le=365),
) -> Response:
    """Serve an iCal calendar feed of Congress committee meetings."""
    window = await load_meetings(
        request,
        chamber=chamber,
        congress=congress,
        days_ahead=days_ahead,
        days_behind=days_behind,
    )

    meetings = window.meetings

    # Filter by committee if requested
    if committee:
        meetings = filter_by_committee(meetings, committee)

    calendar_name = _build_calendar_name(chamber, committee)
    cal = build_calendar(meetings, calendar_name=calendar_name)
    return Response(
        content=calendar_to_bytes(cal),
        media_type="text/calendar",
        headers={"Content-Disposition": "inline; filename=meetings.ics"},
    )


_COMMITTEE_NAMES: dict[str, str] = {
    c["system_code"]: c["name"] for c in COMMITTEES_119
}

_MAX_LISTED = 3


def _build_calendar_name(
    chamber: str | None, committee: str | None
) -> str:
    """Generate a human-readable calendar name from filter parameters."""
    if committee:
        codes = [c.strip().lower() for c in committee.split(",") if c.strip()]
        names = [_COMMITTEE_NAMES[code] for code in codes if code in _COMMITTEE_NAMES]
        if names:
            if len(names) <= _MAX_LISTED:
                return ", ".join(names) + " Meetings"
            listed = ", ".join(names[:_MAX_LISTED])
            return f"{listed} & {len(names) - _MAX_LISTED} More Meetings"

    if chamber == "senate":
        return "Senate Committee Meetings"
    if chamber == "house":
        return "House Committee Meetings"

    return "Congress Committee Meetings"
