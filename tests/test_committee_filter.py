"""Unit tests for committee filtering — no API needed."""

from datetime import datetime, timezone

from congress_calendar.models import CommitteeInfo, CommitteeMeeting
from congress_calendar.routes.calendar_feed import filter_by_committee


def _make_meeting(system_code: str, name: str = "Test Committee") -> CommitteeMeeting:
    return CommitteeMeeting(
        event_id="1",
        date=datetime(2026, 3, 5, 15, 0, 0, tzinfo=timezone.utc),
        title="Test Hearing",
        chamber="house",
        meeting_status="Scheduled",
        building="Rayburn",
        room="2318",
        committees=[CommitteeInfo(name=name, system_code=system_code)],
        congress=119,
    )


def test_exact_match():
    meetings = [_make_meeting("hssy00"), _make_meeting("hsju00")]
    result = filter_by_committee(meetings, "hsju00")
    assert len(result) == 1
    assert result[0].committees[0].system_code == "hsju00"


def test_parent_code_includes_subcommittees():
    meetings = [
        _make_meeting("hssy00"),
        _make_meeting("hssy15"),
        _make_meeting("hssy21"),
        _make_meeting("hsju00"),
    ]
    result = filter_by_committee(meetings, "hssy00")
    assert len(result) == 3
    codes = {m.committees[0].system_code for m in result}
    assert codes == {"hssy00", "hssy15", "hssy21"}


def test_subcommittee_code_does_not_match_parent():
    meetings = [_make_meeting("hssy00"), _make_meeting("hssy15")]
    result = filter_by_committee(meetings, "hssy15")
    assert len(result) == 1
    assert result[0].committees[0].system_code == "hssy15"


def test_multiple_committee_codes():
    meetings = [
        _make_meeting("hssy00"),
        _make_meeting("hssy15"),
        _make_meeting("ssju00"),
        _make_meeting("ssju03"),
        _make_meeting("hsag00"),
    ]
    result = filter_by_committee(meetings, "hssy00,ssju00")
    assert len(result) == 4
    codes = {m.committees[0].system_code for m in result}
    assert codes == {"hssy00", "hssy15", "ssju00", "ssju03"}


def test_case_insensitive():
    meetings = [_make_meeting("HSSY00"), _make_meeting("HSSY15")]
    result = filter_by_committee(meetings, "hssy00")
    assert len(result) == 2


def test_no_matches():
    meetings = [_make_meeting("hssy00")]
    result = filter_by_committee(meetings, "hsju00")
    assert len(result) == 0


def test_whitespace_in_codes():
    meetings = [_make_meeting("hssy00"), _make_meeting("hsju00")]
    result = filter_by_committee(meetings, " hssy00 , hsju00 ")
    assert len(result) == 2
