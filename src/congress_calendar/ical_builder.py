"""Build iCal calendars from committee meeting data."""

from datetime import timedelta

from icalendar import Calendar, Event

from .models import CommitteeMeeting

STATUS_MAP = {
    "scheduled": "CONFIRMED",
    "cancelled": "CANCELLED",
    "canceled": "CANCELLED",
    "postponed": "TENTATIVE",
}

CHAMBER_PREFIX = {
    "senate": "S",
    "house": "H",
}


def build_calendar(meetings: list[CommitteeMeeting]) -> Calendar:
    """Build an iCal calendar from a list of committee meetings."""
    cal = Calendar()
    cal.add("prodid", "-//Congress Calendar//congress-calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Congress Committee Meetings")
    cal.add("x-wr-timezone", "America/New_York")

    for meeting in meetings:
        event = _build_event(meeting)
        cal.add_component(event)

    return cal


def _build_event(meeting: CommitteeMeeting) -> Event:
    """Convert a CommitteeMeeting to an iCal VEVENT."""
    event = Event()

    # UID: stable, unique identifier
    event.add("uid", f"{meeting.event_id}.{meeting.congress}@congress-calendar")

    # Summary: [S] or [H] prefix + first committee name
    prefix = CHAMBER_PREFIX.get(meeting.chamber, "?")
    committee_name = meeting.committees[0].name if meeting.committees else meeting.title
    event.add("summary", f"[{prefix}] {committee_name}")

    # Times
    event.add("dtstart", meeting.date)
    event.add("dtend", meeting.date + timedelta(hours=2))

    # Location
    parts = []
    if meeting.room:
        parts.append(f"Room {meeting.room}")
    if meeting.building:
        parts.append(meeting.building)
    if parts:
        event.add("location", ", ".join(parts))

    # Status
    status = STATUS_MAP.get(meeting.meeting_status.lower(), "CONFIRMED")
    event.add("status", status)

    # Description
    desc_lines = [meeting.title]
    if meeting.committees:
        names = ", ".join(c.name for c in meeting.committees)
        desc_lines.append(f"Committees: {names}")
    if meeting.url:
        desc_lines.append(f"Details: {meeting.url}")
    event.add("description", "\n".join(desc_lines))

    return event


def calendar_to_bytes(cal: Calendar) -> bytes:
    """Serialize an iCal calendar to bytes."""
    return cal.to_ical()
