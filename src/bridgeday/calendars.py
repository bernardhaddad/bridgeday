"""One place that turns the data snapshot into a country's working calendar."""

from __future__ import annotations

from pathlib import Path

from .data import Holiday, load_holidays, load_workdays
from .optimizer import Calendar, weekend_for


def country_calendar(
    data_dir: Path, country: dict, years: range
) -> tuple[dict[int, list[Holiday] | None], Calendar]:
    """Holidays per year (None where there is no data) and the calendar across all of them:
    public holidays off, the country's weekend off, declared weekend workdays on."""
    cc = country["countryCode"]
    loaded = {y: load_holidays(data_dir, y, cc) for y in years}
    off = {h.day for hs in loaded.values() if hs for h in hs if h.day_off}
    workdays = set()
    for y in years:
        workdays |= load_workdays(data_dir, y).get(cc, set())
    return loaded, Calendar(off, weekend_for(cc, country.get("weekend")), workdays)
