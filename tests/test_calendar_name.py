"""Unit tests for dynamic calendar name generation."""

from congress_calendar.routes.calendar_feed import _build_calendar_name


def test_no_filters():
    assert _build_calendar_name(None, None) == "Congress Committee Meetings"


def test_chamber_senate():
    assert _build_calendar_name("senate", None) == "Senate Committee Meetings"


def test_chamber_house():
    assert _build_calendar_name("house", None) == "House Committee Meetings"


def test_single_committee():
    assert _build_calendar_name(None, "ssju00") == "Judiciary Meetings"


def test_two_committees():
    name = _build_calendar_name(None, "ssju00,ssas00")
    assert name == "Judiciary, Armed Services Meetings"


def test_three_committees():
    name = _build_calendar_name(None, "ssju00,ssas00,ssfi00")
    assert name == "Judiciary, Armed Services, Finance Meetings"


def test_four_committees_truncates():
    name = _build_calendar_name(None, "ssju00,ssas00,ssfi00,ssfr00")
    assert name == "Judiciary, Armed Services, Finance & 1 More Meetings"


def test_many_committees_truncates():
    codes = "ssju00,ssas00,ssfi00,ssfr00,ssbu00,ssap00"
    name = _build_calendar_name(None, codes)
    assert name == "Judiciary, Armed Services, Finance & 3 More Meetings"


def test_committee_overrides_chamber():
    name = _build_calendar_name("senate", "ssju00")
    assert name == "Judiciary Meetings"


def test_unknown_code_ignored():
    name = _build_calendar_name(None, "zzz999")
    assert name == "Congress Committee Meetings"


def test_whitespace_in_codes():
    name = _build_calendar_name(None, " ssju00 , ssas00 ")
    assert name == "Judiciary, Armed Services Meetings"
