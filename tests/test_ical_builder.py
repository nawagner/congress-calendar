"""Unit tests for iCal builder — no API needed."""

from datetime import datetime, timezone

from congress_calendar.ical_builder import build_calendar, calendar_to_bytes
from congress_calendar.models import CommitteeInfo, CommitteeMeeting


def _make_meeting(**overrides) -> CommitteeMeeting:
    defaults = {
        "event_id": "12345",
        "date": datetime(2026, 3, 5, 15, 0, 0, tzinfo=timezone.utc),
        "title": "Hearing on AI Policy",
        "chamber": "senate",
        "meeting_status": "Scheduled",
        "building": "Dirksen Senate Office Building",
        "room": "419",
        "committees": [CommitteeInfo(name="Senate Judiciary Committee", system_code="ssju00")],
        "congress": 119,
        "url": "https://www.congress.gov/event/119th-congress/senate-event/12345",
    }
    defaults.update(overrides)
    return CommitteeMeeting(**defaults)


def test_build_calendar_properties():
    cal = build_calendar([_make_meeting()])
    ical = cal.to_ical().decode()
    assert "PRODID:-//Congress Calendar//congress-calendar//EN" in ical
    assert "X-WR-CALNAME:Congress Committee Meetings" in ical
    assert "X-WR-TIMEZONE:America/New_York" in ical


def test_vevent_uid():
    cal = build_calendar([_make_meeting(event_id="99999")])
    ical = cal.to_ical().decode()
    assert "99999.119@congress-calendar" in ical


def test_vevent_summary_senate():
    cal = build_calendar([_make_meeting(chamber="senate")])
    ical = cal.to_ical().decode()
    assert "[S] Senate Judiciary Committee" in ical


def test_vevent_summary_house():
    meeting = _make_meeting(
        chamber="house",
        committees=[CommitteeInfo(name="House Armed Services", system_code="hsas00")],
    )
    cal = build_calendar([meeting])
    ical = cal.to_ical().decode()
    assert "[H] House Armed Services" in ical


def test_vevent_location():
    cal = build_calendar([_make_meeting()])
    ical = cal.to_ical().decode()
    assert "Room 419" in ical
    assert "Dirksen Senate Office Building" in ical


def test_vevent_status_scheduled():
    cal = build_calendar([_make_meeting(meeting_status="Scheduled")])
    ical = cal.to_ical().decode()
    assert "STATUS:CONFIRMED" in ical


def test_vevent_status_cancelled():
    cal = build_calendar([_make_meeting(meeting_status="Cancelled")])
    ical = cal.to_ical().decode()
    assert "STATUS:CANCELLED" in ical


def test_vevent_status_postponed():
    cal = build_calendar([_make_meeting(meeting_status="Postponed")])
    ical = cal.to_ical().decode()
    assert "STATUS:TENTATIVE" in ical


def test_vevent_description_contains_title():
    cal = build_calendar([_make_meeting(title="Test Hearing Title")])
    ical = cal.to_ical().decode()
    assert "Test Hearing Title" in ical


def test_calendar_to_bytes():
    cal = build_calendar([_make_meeting()])
    data = calendar_to_bytes(cal)
    assert isinstance(data, bytes)
    assert data.startswith(b"BEGIN:VCALENDAR")
    assert data.strip().endswith(b"END:VCALENDAR")


def test_empty_calendar():
    cal = build_calendar([])
    ical = cal.to_ical().decode()
    assert "BEGIN:VCALENDAR" in ical
    assert "VEVENT" not in ical


def test_custom_calendar_name():
    cal = build_calendar([_make_meeting()], calendar_name="Senate Judiciary Meetings")
    ical = cal.to_ical().decode()
    assert "X-WR-CALNAME:Senate Judiciary Meetings" in ical


def test_multiple_meetings():
    meetings = [
        _make_meeting(event_id="111"),
        _make_meeting(event_id="222"),
    ]
    cal = build_calendar(meetings)
    ical = cal.to_ical().decode()
    assert ical.count("BEGIN:VEVENT") == 2
