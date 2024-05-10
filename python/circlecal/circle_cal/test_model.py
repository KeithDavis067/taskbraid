import pytest
from datetime import datetime
from .model import CalendarElement, TimeDigit, UNITS


class Test_CalendarElement:
    def test_unit(self):
        ce = CalendarElement(year=2024)
        assert ce.unit == "year"

        assert ce.year.value == 2024
        assert ce.superunit is None
        assert ce.subunit == "month"
        assert ce.digit == TimeDigit("year", 2024)
        assert ce.year.value == 2024

    def test__contains__(self):
        jan1 = datetime(2024, 1, 1)
        assert jan1 > CalendarElement(year=2023)
        assert jan1 in CalendarElement(year=2024)
        assert jan1 < CalendarElement(year=2025)
        assert jan1 in CalendarElement(year=2024, month=1)
        assert jan1 not in CalendarElement(year=2024, month=2)
        assert jan1 not in CalendarElement(year=2024, month=2, day=1)

    def test_init(self):
        ce = CalendarElement(year=1, microsecond=0)
        assert ce.unit == "microsecond"
        assert ce.subunit is None
        assert ce.superunit == "second"
        for u in UNITS:
            assert getattr(ce, u).value == ce.digits[u].range.start

        ce = CalendarElement(year=2024, hour=1)
        assert ce.unit == "hour"
        assert ce.subunit == "minute"
        assert ce.day.value == 1

    def test_set(self):
        ce = CalendarElement(year=2024, minute=0)
        assert ce.unit == "minute"
        ce.second = 0
        assert ce.unit == "second"
        ce = CalendarElement(year=2024, day=1)
        ce.microsecond == 0
        for u in UNITS:
            if u == "year":
                assert getattr(ce, u).value == 2024
            else:
                assert getattr(ce, u).value == getattr(ce, u).range.start

    def test_unset(self):
        ce = CalendarElement(year=2024, day=1)
        assert ce.unit == "day"
        ce.day == None
        assert ce.unit == "month"
