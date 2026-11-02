"""The paid product: a printable leave and holiday planner for one country and year."""

from __future__ import annotations

import calendar
from datetime import date

from .data import Holiday
from .optimizer import BudgetPlan, Calendar, Window
from .pdf import Document, Page
from .render import fmt, plural, span

INK = (0.11, 0.12, 0.14)
MUTED = (0.42, 0.45, 0.50)
ACCENT = (0.04, 0.43, 0.31)
HOL = (0.89, 0.34, 0.18)
HOL_SOFT = (0.99, 0.91, 0.88)
LV = (0.95, 0.69, 0.20)
LV_SOFT = (1.00, 0.95, 0.84)
WE = (0.93, 0.92, 0.89)
RULE = (0.84, 0.83, 0.79)
WHITE = (1.0, 1.0, 1.0)
M = 36.0  # page margin
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class Planner:
    def __init__(
        self,
        *,
        cc: str,
        country: str,
        year: int,
        holidays: list[Holiday],
        cal: Calendar,
        weekend: str,
        plans: list[Window],
        budgets: list[BudgetPlan],
        site: str,
        url: str,
    ):
        self.cc, self.country, self.year = cc, country, year
        self.holidays = [h for h in holidays if h.day.year == year]
        self.cal, self.weekend, self.plans, self.budgets = cal, weekend, plans, budgets
        self.site, self.url = site, url
        self.names: dict[date, str] = {}
        for h in self.holidays:
            if h.day_off:
                self.names.setdefault(h.day, h.name)
        b10 = next((b for b in budgets if b.budget == 10), None)
        self.focus = b10 or (budgets[0] if budgets else None)
        self.leave = {d for w in (self.focus.windows if self.focus else ()) for d in w.leave}
        self.doc = Document(f"{country} {year} leave and holiday planner")

    # -- helpers -----------------------------------------------------------------------
    def _page(self, title: str, subtitle: str = "") -> Page:
        p = self.doc.page()
        p.rect(0, 0, p.w, 6, fill=ACCENT)
        p.text(M, 46, title, size=22, bold=True)
        if subtitle:
            p.text(M, 64, subtitle, size=10, color=MUTED, max_width=p.w - 2 * M)
        n = len(self.doc.pages)
        p.text(M, p.h - 18, f"{self.site} · {self.url}", size=7.5, color=MUTED)
        p.text(
            p.w - M,
            p.h - 18,
            f"{self.country} {self.year} · {n}",
            size=7.5,
            color=MUTED,
            align="right",
        )
        return p

    def _kind(self, d: date) -> str:
        if d in self.names:
            return "hol"
        if d in self.leave:
            return "lv"
        if self.cal.is_off(d):
            return "we"
        return ""

    def _legend(self, p: Page, x: float, y: float) -> None:
        for fill, label in ((HOL, "Public holiday"), (LV, "Suggested leave"), (WE, "Weekend")):
            p.rect(x, y - 8, 10, 10, fill=fill)
            p.text(x + 14, y, label, size=8.5, color=MUTED)
            x += 104

    # -- pages -------------------------------------------------------------------------
    def cover(self) -> None:
        p = self.doc.page()
        p.rect(0, 0, p.w, p.h, fill=(0.98, 0.98, 0.97))
        p.rect(0, 0, 18, p.h, fill=ACCENT)
        p.text(70, 150, f"{self.year}", size=64, bold=True, color=ACCENT)
        p.text(70, 205, self.country, size=36, bold=True, max_width=p.w - 140)
        p.text(70, 238, "Leave & Holiday Planner", size=20, color=MUTED)
        days_off = sorted(self.names)
        weekday = sum(1 for d in days_off if not self.cal.is_weekend(d))
        stats = [
            (str(len(days_off)), "nationwide public holidays"),
            (str(weekday), "of them on a working day"),
        ]
        if self.focus and self.focus.days_off:
            stats.append(
                (f"{self.focus.leave_used} → {self.focus.days_off}", "leave days → days off")
            )
        x = 70
        for big, small in stats:
            p.rect(x, 300, 200, 92, fill=WHITE, stroke=RULE)
            p.text(x + 16, 346, big, size=28, bold=True, color=ACCENT)
            p.text(x + 16, 372, small, size=10, color=MUTED, max_width=172)
            x += 216
        p.text(70, 450, "More time with the people you love, from the same days of leave.", size=12)
        p.text(
            70,
            470,
            f"Weekend: {self.weekend}. Plans count nationwide public holidays only.",
            size=9,
            color=MUTED,
        )
        p.text(70, p.h - 40, f"{self.site} · {self.url}", size=9, color=MUTED)

    def year_at_a_glance(self) -> None:
        p = self._page(f"{self.year} at a glance", "Your 10-day leave plan is marked in amber.")
        self._legend(p, p.w - M - 300, 46)
        cols, gap = 4, 18
        bw = (p.w - 2 * M - gap * (cols - 1)) / cols
        cw, ch = bw / 7, 17.5
        for m in range(1, 13):
            col, row = (m - 1) % cols, (m - 1) // cols
            x0, y0 = M + col * (bw + gap), 90 + row * 158
            p.text(x0, y0, calendar.month_name[m], size=11, bold=True)
            for i, dn in enumerate(DAYS):
                p.text(x0 + i * cw + cw / 2, y0 + 15, dn[0], size=7, color=MUTED, align="center")
            first = date(self.year, m, 1)
            for day in range(1, calendar.monthrange(self.year, m)[1] + 1):
                d = date(self.year, m, day)
                idx = first.weekday() + day - 1
                cx, cy = x0 + (idx % 7) * cw, y0 + 20 + (idx // 7) * ch
                kind = self._kind(d)
                fill = {"hol": HOL, "lv": LV, "we": WE}.get(kind)
                if fill:
                    p.rect(cx + 1, cy + 1, cw - 2, ch - 2, fill=fill)
                color = WHITE if kind == "hol" else INK
                p.text(
                    cx + cw / 2,
                    cy + 12.5,
                    str(day),
                    size=8,
                    bold=kind in ("hol", "lv"),
                    color=color,
                    align="center",
                )

    def best_breaks(self) -> None:
        p = self._page("Your best breaks", f"Weekend: {self.weekend}. Book the leave days early.")
        y = 96
        p.text(M, y, "Best value: most days off per leave day", size=12, bold=True, color=ACCENT)
        y += 10
        for w in self.plans[:9]:
            y += 40
            p.rect(M, y - 30, 360, 36, fill=WHITE, stroke=RULE)
            p.text(
                M + 10,
                y - 14,
                f"{plural(w.cost, 'day')} off → {w.length} days",
                size=10.5,
                bold=True,
            )
            p.text(M + 190, y - 14, span(w), size=10, color=ACCENT, max_width=160)
            leave = "Leave: " + ", ".join(fmt(d) for d in w.leave)
            hols = " · ".join(self.names[d] for d in w.holidays if d in self.names)
            p.text(M + 10, y - 1, f"{leave} · {hols}", size=7.5, color=MUTED, max_width=340)
        if not self.plans:
            p.text(M, y + 30, "No weekday holidays to bridge this year.", size=10, color=MUTED)
        x = M + 400
        y = 96
        p.text(x, y, "If you have 5, 10 or 15 days of leave", size=12, bold=True, color=ACCENT)
        for b in self.budgets:
            y += 30
            p.text(x, y, f"{b.budget} days of leave: {b.days_off} days off", size=11, bold=True)
            p.text(x + 330, y, f"uses {b.leave_used}", size=8.5, color=MUTED, align="right")
            for w in b.windows:
                y += 15
                p.text(x + 10, y, f"{span(w)}  ({plural(w.cost, 'day')} → {w.length})", size=9)
            y += 6
            p.line(x, y, x + 330, y, RULE)

    def holiday_list(self) -> None:
        rows = self.holidays
        per = 24
        for start in range(0, max(len(rows), 1), per):
            more = " (continued)" if start else ""
            p = self._page(
                f"Public holidays {self.year}{more}", "Regional holidays apply only where listed."
            )
            y = 92
            for label, x in (
                ("Date", M),
                ("Holiday", M + 110),
                ("Where", M + 450),
                ("Type", M + 650),
            ):
                p.text(x, y, label, size=8.5, bold=True, color=MUTED)
            p.line(M, y + 6, p.w - M, y + 6, RULE)
            for h in rows[start : start + per]:
                y += 18
                color = INK if h.nationwide else MUTED
                p.text(M, y, fmt(h.day), size=9.5, bold=h.day_off, color=color)
                p.text(M + 110, y, h.name, size=9.5, color=color, max_width=330)
                where = "Nationwide" if h.nationwide else "Regional: " + ", ".join(h.regions)
                p.text(M + 450, y, where, size=8.5, color=color, max_width=190)
                p.text(M + 650, y, ", ".join(h.types), size=8.5, color=MUTED, max_width=120)
            if not rows:
                p.text(M, y + 20, "No holidays listed for this year.", size=10, color=MUTED)

    def month(self, m: int) -> None:
        name = calendar.month_name[m]
        in_month = [d for d in sorted(self.names) if d.month == m]
        sub = (
            ", ".join(f"{fmt(d)} {self.names[d]}" for d in in_month)
            or "No public holidays this month"
        )
        p = self._page(f"{name} {self.year}", sub)
        self._legend(p, p.w - M - 300, 46)
        first = date(self.year, m, 1)
        n_days = calendar.monthrange(self.year, m)[1]
        rows = (first.weekday() + n_days + 6) // 7
        top, cw = 82, (p.w - 2 * M) / 7
        ch = (p.h - top - 40 - 16) / rows
        for i, dn in enumerate(DAYS):
            p.text(M + i * cw + 6, top + 10, dn, size=9, bold=True, color=MUTED)
        for idx in range(rows * 7):
            x, y = M + (idx % 7) * cw, top + 16 + (idx // 7) * ch
            day = idx - first.weekday() + 1
            if not 1 <= day <= n_days:
                p.rect(x, y, cw, ch, fill=(0.97, 0.97, 0.96), stroke=RULE)
                continue
            d = date(self.year, m, day)
            kind = self._kind(d)
            fill = {"hol": HOL_SOFT, "lv": LV_SOFT, "we": WE}.get(kind, WHITE)
            p.rect(x, y, cw, ch, fill=fill, stroke=RULE)
            p.text(x + 6, y + 15, str(day), size=12, bold=True, color=HOL if kind == "hol" else INK)
            if kind == "hol":
                p.text(
                    x + 6, y + 29, self.names[d], size=7.5, bold=True, color=HOL, max_width=cw - 12
                )
            elif kind == "lv":
                p.text(x + 6, y + 29, "Take leave", size=7.5, bold=True, color=(0.6, 0.4, 0.0))

    def tracker(self) -> None:
        p = self._page("Leave tracker", "Fill in your allowance, then log each day as you book it.")
        x = M
        for label in ("Allowance", "Booked", "Taken", "Left"):
            p.rect(x, 80, 180, 54, fill=WHITE, stroke=RULE)
            p.text(x + 12, 98, label, size=9, bold=True, color=MUTED)
            x += 192
        y = 160
        heads = (
            ("Month", M),
            ("Planned dates", M + 110),
            ("Days", M + 420),
            ("Booked?", M + 480),
            ("Notes", M + 560),
        )
        for label, hx in heads:
            p.text(hx, y, label, size=8.5, bold=True, color=MUTED)
        for m in range(1, 13):
            y += 29
            p.line(M, y + 8, p.w - M, y + 8, RULE)
            p.text(M, y, calendar.month_name[m], size=10)
            p.rect(M + 488, y - 9, 11, 11, stroke=MUTED)

    def bytes(self) -> bytes:
        self.cover()
        self.year_at_a_glance()
        self.best_breaks()
        self.holiday_list()
        for m in range(1, 13):
            self.month(m)
        self.tracker()
        return self.doc.bytes()
