"""Pydantic models for committee meeting data."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

_EVENT_URL_CHAMBERS = {"house", "senate"}


def format_location(building: str, room: str) -> str:
    """Render a human-readable location, e.g. "Room 419, Dirksen Senate Office Building"."""
    parts = []
    if room:
        parts.append(f"Room {room}")
    if building:
        parts.append(building)
    return ", ".join(parts)


def ordinal(n: int) -> str:
    """Render an integer with its English ordinal suffix, e.g. 119 -> "119th"."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class CommitteeInfo(BaseModel):
    name: str
    system_code: str


class CommitteeMeeting(BaseModel):
    event_id: str
    date: datetime
    title: str
    chamber: str
    meeting_status: str
    building: str
    room: str
    committees: list[CommitteeInfo]
    congress: int
    url: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any], congress: int) -> "CommitteeMeeting":
        """Parse a committee meeting from the Congress.gov API response."""
        location = data.get("location", {}) or {}
        committees = [
            CommitteeInfo(
                name=c.get("name", "Unknown Committee"),
                system_code=c.get("systemCode", ""),
            )
            for c in (data.get("committees") or [])
        ]

        event_id = str(data.get("eventId", ""))
        chamber = data.get("chamber", "unknown").lower()

        return cls(
            event_id=event_id,
            date=datetime.fromisoformat(data["date"]),
            title=data.get("title", "Committee Meeting"),
            chamber=chamber,
            meeting_status=data.get("meetingStatus", "Scheduled"),
            building=location.get("building", ""),
            room=location.get("room", ""),
            committees=committees,
            congress=congress,
            url=data.get("url"),
        )

    @property
    def public_url(self) -> str | None:
        """A congress.gov page a person can open, or None if one can't be built."""
        if self.url and self.url.startswith("https://www.congress.gov/"):
            return self.url
        if not self.event_id or self.chamber not in _EVENT_URL_CHAMBERS:
            return None
        return (
            f"https://www.congress.gov/event/{ordinal(self.congress)}-congress/"
            f"{self.chamber}-event/{self.event_id}"
        )

    def to_summary_dict(self) -> dict[str, Any]:
        """Serialize for the JSON API consumed by the browse view."""
        # Congress.gov returns UTC timestamps; if one ever arrives without an
        # offset, stamp it so browsers don't parse it as the viewer's local time.
        when = self.date if self.date.tzinfo else self.date.replace(tzinfo=UTC)
        return {
            "event_id": self.event_id,
            "date": when.isoformat(),
            "title": self.title,
            "chamber": self.chamber,
            "status": self.meeting_status,
            "location": format_location(self.building, self.room),
            "committees": [
                {"name": c.name, "system_code": c.system_code} for c in self.committees
            ],
            "url": self.public_url,
        }
