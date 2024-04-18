import pytest
from model import CalendarElement, TimeDigit


def Test_CalendarElement:
    def test_unit():
        ce = CalendarElement(year="2024")
        assert ce.unit == "year"

        assert ce.year.value == 2024
        assert ce.superunit is None
        assert ce.subunit == "month"
        assert ce.digit == TimeDigit("year", 2024)
        assert ce.year == 2024
