"""Turn a holiday calendar into the best ways to spend leave days.

A "window" is a run of consecutive days that is maximal: the day before and the day
after are working days, so it cannot be stretched for free. Its cost is the number of
working days inside it (the leave you must take); its value is its length.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DAY = timedelta(days=1)
MAX_WINDOW = 31  # long enough for dense clusters such as Russia's January
BUDGETS = (5, 10, 15)

# ISO weekday numbers (Mon=1 .. Sun=7). Default is Saturday-Sunday.
FRI_SAT = frozenset({5, 6})
FRI = frozenset({5})
WEEKENDS: dict[str, frozenset[int]] = {
    **{cc: FRI_SAT for cc in ("BD", "BH", "DZ", "EG", "IQ", "LY", "SD", "SY", "YE")},
    **{cc: FRI for cc in ("DJ", "SO")},
}
DEFAULT_WEEKEND = frozenset({6, 7})
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def weekend_for(cc: str, days: list[int] | None = None) -> frozenset[int]:
    """The country's weekend as ISO weekdays. `days` comes from the data (the holidays
    library knows each country's official weekend); the table is the fallback."""
    if days:
        return frozenset(int(d) for d in days if 1 <= int(d) <= 7)
    return WEEKENDS.get(cc.upper(), DEFAULT_WEEKEND)


def weekend_label(cc: str, days: list[int] | None = None) -> str:
    return " and ".join(DAY_NAMES[d - 1] for d in sorted(weekend_for(cc, days)))


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    leave: tuple[date, ...]
    holidays: tuple[date, ...]

    @property
    def length(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def cost(self) -> int:
        return len(self.leave)

    @property
    def ratio(self) -> float:
        return self.length / self.cost if self.cost else float("inf")


class Calendar:
    def __init__(
        self, off_holidays: set[date], weekend: frozenset[int], workdays: set[date] | None = None
    ):
        self.holidays = off_holidays
        self.weekend = weekend
        self.workdays = workdays or set()  # weekend days declared working days

    def is_weekend(self, d: date) -> bool:
        return d.isoweekday() in self.weekend and d not in self.workdays

    def is_off(self, d: date) -> bool:
        return d in self.holidays or self.is_weekend(d)

    def window(self, start: date, end: date) -> Window:
        days = [start + i * DAY for i in range((end - start).days + 1)]
        return Window(
            start,
            end,
            tuple(d for d in days if not self.is_off(d)),
            tuple(d for d in days if d in self.holidays),
        )

    def candidates(self, year: int, max_cost: int, after: date | None = None) -> list[Window]:
        """Every maximal window starting in `year` that costs between 1 and max_cost days."""
        out = []
        first = date(year, 1, 1)
        d = max(first, after - MAX_WINDOW * DAY) if after else first
        while d.year == year:
            if not self.is_off(d - DAY):
                cost = 0
                for n in range(MAX_WINDOW):
                    e = d + n * DAY
                    if not self.is_off(e):
                        cost += 1
                        if cost > max_cost:
                            break
                    if cost and not self.is_off(e + DAY):
                        w = self.window(d, e)
                        if not after or w.leave[0] >= after:  # leave still bookable
                            out.append(w)
            d += DAY
        return out

    def free_breaks(self, year: int, min_len: int = 3, after: date | None = None) -> list[Window]:
        """Runs of off days of at least min_len that include a holiday and cost nothing."""
        out = []
        d = date(year, 1, 1)
        while d.year == year:
            if self.is_off(d) and not self.is_off(d - DAY):
                e = d
                while self.is_off(e + DAY):
                    e += DAY
                w = self.window(d, e)
                if w.length >= min_len and w.holidays and (not after or w.end >= after):
                    out.append(w)
                d = e
            d += DAY
        return out


def weekday_holidays(w: Window, cal: Calendar) -> int:
    return sum(1 for h in w.holidays if not cal.is_weekend(h))


def worth_it(w: Window, cal: Calendar) -> bool:
    """A break worth planning: it bridges a weekday holiday, or it is a full week away.
    Without this rule, single Fridays win by counting weekends you already had."""
    return w.length >= 4 and (weekday_holidays(w, cal) > 0 or w.length >= 9)


def best_plans(
    cal: Calendar, year: int, max_cost: int = 5, limit: int = 8, after: date | None = None
) -> list[Window]:
    """The highest days-off-per-leave-day windows that exist thanks to a weekday holiday,
    no two overlapping, in date order."""
    pool = [
        w
        for w in cal.candidates(year, max_cost, after)
        if weekday_holidays(w, cal) and w.length >= 4
    ]
    pool.sort(key=lambda w: (-w.ratio, -w.length, w.start))
    chosen: list[Window] = []
    for w in pool:
        if all(w.end < c.start or w.start > c.end for c in chosen):
            chosen.append(w)
            if len(chosen) == limit:
                break
    return sorted(chosen, key=lambda w: w.start)


@dataclass(frozen=True)
class BudgetPlan:
    budget: int
    windows: tuple[Window, ...]

    @property
    def leave_used(self) -> int:
        return sum(w.cost for w in self.windows)

    @property
    def days_off(self) -> int:
        return sum(w.length for w in self.windows)


def best_budget(cal: Calendar, year: int, budget: int, after: date | None = None) -> BudgetPlan:
    """Non-overlapping windows using at most `budget` leave days that maximise days off.

    Only windows that are worth_it() count. Weighted interval scheduling with a knapsack
    dimension: f[i][b] is the most days off using the first i windows (sorted by end) and
    b leave days. Ties prefer fewer windows.
    """
    ws = sorted(
        (w for w in cal.candidates(year, budget, after) if worth_it(w, cal)),
        key=lambda w: (w.end, w.start),
    )
    ends = [w.end for w in ws]
    prev = []
    for w in ws:
        lo, hi = 0, len(ends)
        while lo < hi:  # count of windows ending strictly before w starts
            mid = (lo + hi) // 2
            if ends[mid] < w.start:
                lo = mid + 1
            else:
                hi = mid
        prev.append(lo)
    f = [[(0, 0)] * (budget + 1)]
    for i, w in enumerate(ws):
        row = list(f[i])
        base = f[prev[i]]
        for b in range(w.cost, budget + 1):
            days, n = base[b - w.cost]
            cand = (days + w.length, n - 1)
            if cand > row[b]:
                row[b] = cand
        f.append(row)
    best_b = max(range(budget + 1), key=lambda b: (f[-1][b], -b)) if ws else 0
    chosen = []
    i, b = len(ws), best_b
    while i > 0 and f[i][b][0] > 0:
        if f[i][b] == f[i - 1][b]:
            i -= 1
            continue
        w = ws[i - 1]
        chosen.append(w)
        b -= w.cost
        i = prev[i - 1]
    return BudgetPlan(budget, tuple(sorted(chosen, key=lambda w: w.start)))
