"""Pydantic models for committee meeting data."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
