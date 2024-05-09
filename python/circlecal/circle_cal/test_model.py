import pytest
from datetime import datetime
from .model import CalendarElement, TimeDigit


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
