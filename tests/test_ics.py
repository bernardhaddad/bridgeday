from datetime import UTC, date, datetime

from bridgeday.data import Holiday
from bridgeday.ics import calendar


def h(day, name, nationwide=True):
    return Holiday(day, name, name, nationwide, nationwide, (), ("Public",))


def test_calendar_is_valid_rfc5545():
    hols = [
        h(date(2027, 1, 1), "New Year, Day; one"),
        h(date(2027, 3, 8), "Regional only", nationwide=False),
        h(date(2027, 5, 6), "A" * 120),
    ]
    out = calendar("DE", "Germany", 2027, hols, datetime(2027, 1, 1, tzinfo=UTC))
    lines = out.split("\r\n")
    assert out.endswith("\r\n") and lines[0] == "BEGIN:VCALENDAR"
    assert out.count("BEGIN:VEVENT") == 2  # regional holiday left out
    assert r"SUMMARY:New Year\, Day\; one" in out
    assert "DTSTART;VALUE=DATE:20270101" in out and "DTEND;VALUE=DATE:20270102" in out
    assert all(len(line.encode()) <= 75 for line in lines)
    again = calendar("DE", "Germany", 2027, hols, datetime(2027, 1, 1, tzinfo=UTC))
    assert again == out  # stable UIDs across builds
