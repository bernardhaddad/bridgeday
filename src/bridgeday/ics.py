"""RFC 5545 calendar of one country's holidays for one year."""

from __future__ import annotations

import zlib
from datetime import datetime, timedelta

from .data import Holiday


def _text(s: str) -> str:
    s = s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return s.replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """Lines longer than 75 octets continue on the next line after one space."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode())
            cur = b""
        cur += b
    out.append(cur.decode())
    return [out[0]] + [" " + x for x in out[1:]]


def calendar(cc: str, country: str, year: int, holidays: list[Holiday], stamp: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//bridgeday//holidays//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_text(f'{country} public holidays {year}')}",
    ]
    seen = set()
    for h in holidays:
        if h.day.year != year or not h.nationwide or (h.day, h.name) in seen:
            continue
        seen.add((h.day, h.name))
        uid = f"{h.day:%Y%m%d}-{cc.lower()}-{zlib.crc32(h.name.encode()):08x}@bridgeday"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp:%Y%m%dT%H%M%SZ}",
            f"DTSTART;VALUE=DATE:{h.day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{h.day + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_text(h.name)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(x + "\r\n" for line in lines for x in _fold(line))
