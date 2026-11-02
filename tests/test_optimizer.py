from datetime import date

from bridgeday.optimizer import (
    DEFAULT_WEEKEND,
    Calendar,
    best_budget,
    best_plans,
    weekend_for,
    weekend_label,
)


def test_thursday_holiday_bridges_with_one_friday():
    cal = Calendar({date(2027, 5, 6)}, DEFAULT_WEEKEND)  # Ascension, Thursday
    plans = best_plans(cal, 2027)
    assert plans[0].start == date(2027, 5, 6) and plans[0].end == date(2027, 5, 9)
    assert plans[0].leave == (date(2027, 5, 7),)
    assert plans[0].length == 4 and plans[0].cost == 1


def test_plans_need_a_weekday_holiday():
    assert best_plans(Calendar(set(), DEFAULT_WEEKEND), 2027) == []
    saturday = Calendar({date(2027, 5, 8)}, DEFAULT_WEEKEND)
    assert best_plans(saturday, 2027) == []


def test_plans_do_not_overlap_and_are_sorted():
    cal = Calendar({date(2027, 5, 6), date(2027, 5, 17), date(2027, 12, 24)}, DEFAULT_WEEKEND)
    plans = best_plans(cal, 2027)
    for a, b in zip(plans, plans[1:], strict=False):
        assert a.end < b.start


def test_windows_are_maximal():
    cal = Calendar({date(2027, 5, 6)}, DEFAULT_WEEKEND)
    for w in cal.candidates(2027, 3):
        assert not cal.is_off(w.start.fromordinal(w.start.toordinal() - 1))
        assert not cal.is_off(w.end.fromordinal(w.end.toordinal() + 1))


def test_budget_without_holidays_is_whole_weeks():
    cal = Calendar(set(), DEFAULT_WEEKEND)
    assert best_budget(cal, 2027, 5).days_off == 9
    assert best_budget(cal, 2027, 10).days_off == 18
    b15 = best_budget(cal, 2027, 15)
    assert b15.days_off == 27 and b15.leave_used == 15


def test_budget_respects_limit_and_never_overlaps():
    hols = {date(2027, 1, 1), date(2027, 3, 26), date(2027, 3, 29), date(2027, 5, 6)}
    cal = Calendar(hols, DEFAULT_WEEKEND)
    for budget in (1, 3, 5, 10):
        plan = best_budget(cal, 2027, budget)
        assert plan.leave_used <= budget
        ws = plan.windows
        for a, b in zip(ws, ws[1:], strict=False):
            assert a.end < b.start
    assert best_budget(cal, 2027, 1).days_off == 5  # Thu before Good Friday, Easter Monday


def test_budget_beats_any_single_window():
    hols = {date(2027, 5, 6), date(2027, 12, 24), date(2027, 12, 31)}
    cal = Calendar(hols, DEFAULT_WEEKEND)
    best_single = max(w.length for w in cal.candidates(2027, 5))
    assert best_budget(cal, 2027, 5).days_off >= best_single


def test_window_can_run_into_next_year():
    cal = Calendar({date(2027, 12, 31), date(2028, 1, 3)}, DEFAULT_WEEKEND)
    assert any(w.end.year == 2028 for w in cal.candidates(2027, 2))


def test_friday_saturday_weekend():
    assert weekend_for("eg") == frozenset({5, 6})
    assert weekend_label("EG") == "Friday and Saturday"
    assert weekend_label("DE") == "Saturday and Sunday"
    cal = Calendar({date(2027, 7, 1)}, weekend_for("EG"))  # Thursday, next to Friday
    breaks = cal.free_breaks(2027)
    assert [(w.start, w.end) for w in breaks] == [(date(2027, 7, 1), date(2027, 7, 3))]


def test_after_skips_the_past():
    cal = Calendar({date(2027, 5, 6), date(2027, 12, 24)}, DEFAULT_WEEKEND)
    plans = best_plans(cal, 2027, after=date(2027, 6, 1))
    assert plans and all(w.start >= date(2027, 6, 1) for w in plans)
    plan = best_budget(cal, 2027, 10, after=date(2027, 6, 1))
    assert all(w.start >= date(2027, 6, 1) for w in plan.windows)


def test_window_already_started_still_offered_while_its_leave_is_ahead():
    # Sat 19 Dec 2026 to Sun 27 Dec: leave Mon 21 to Wed 23, Christmas Thu 24 + Fri 25.
    cal = Calendar({date(2026, 12, 24), date(2026, 12, 25)}, DEFAULT_WEEKEND)
    before = best_budget(cal, 2026, 5, after=date(2026, 12, 19))
    sunday = best_budget(cal, 2026, 5, after=date(2026, 12, 20))
    assert before.days_off == sunday.days_off
    assert all(w.leave[0] >= date(2026, 12, 20) for w in sunday.windows)


def test_long_holiday_clusters_are_not_cut_off():
    # Russia-style: 1 to 8 January off, plus a bridge either side.
    hols = {date(2027, 1, d) for d in range(1, 9)}
    cal = Calendar(hols, DEFAULT_WEEKEND)
    assert max(w.length for w in cal.candidates(2027, 5)) >= 17


def test_bangladesh_weekend_is_friday_saturday():
    assert weekend_label("BD") == "Friday and Saturday"
