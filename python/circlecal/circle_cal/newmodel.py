import calendar
from datetime import datetime, timedelta, date, time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from calendar import monthrange, month_name, day_name
from workalendar.usa import UnitedStates, Indiana
from pytz import timezone


ETZ = timezone("America/New_York")

try:
    from skyfield.api import load
    from skyfield import almanac
    skyfield = True
except ImportError:
    skyfield = False

try:
    import pandas as pd
except ImportError:
    pass

# TODO: Figure out how to import pytest only when testing.
try:
    import pytest
except ImportError:
    pytest = False


def _unit_pl(unit):
    if unit[-1] == "s":
        units = unit
        unit = unit[:-1]
    else:
        unit = unit
        units = unit + "s"
    return (unit, units)


RANGES = {"year": range(date.min.year, date.max.year + 1),
          "month": range(1, 13),
          "day": None,
          "hour": range(0, 24),
          "minute": range(0, 60),
          "second": range(0, 60),
          "microsecond": range(0, 1000000)}

UNITS = list(RANGES.keys())


def _subunit(unit):
    if unit == UNITS[-1]:
        return None
    return UNITS[UNITS.index(unit) + 1]


def test_subunit():
    assert _subunit("year") == "month"
    assert _subunit("microsecond") is None


def _subunits(unit):
    u = _unit_pl(unit)[0]
    if u == UNITS[-1]:
        return []
    return UNITS[UNITS.index(unit) + 1:]


def is_subunit(left, right):
    if left in _subunits(right):
        return True
    return False


def test_subunits():
    assert _subunits("second") == ["microsecond"]
    assert _subunits("minute") == ["second", "microsecond"]
    assert _subunits("microsecond") == []


def _superunit(unit):
    u = _unit_pl(unit)[0]
    if u == UNITS[0]:
        return None
    return UNITS[UNITS.index(unit) - 1]


def test_superunit():
    assert _superunit("year") is None
    assert _superunit("microsecond") == "second"


def _superunits(unit):
    u = _unit_pl(unit)[0]
    if u == UNITS[0]:
        return []
    ru = list(reversed(UNITS))
    return ru[ru.index(unit) + 1:]


def is_superunit(left, right):
    if left in _superunits(right):
        return True
    return False


def test_superunits():
    assert _superunits("month") == ["year"]
    assert _superunits("day") == ["month", "year"]
    assert _superunits("year") == []


class TUnit:
    UNITS = UNITS
    RANGES = RANGES

    @property
    def subunit(self):
        return _subunit(self)

    @property
    def superunit(self):
        return _superunit(self)

    def __init__(self, name):
        if name not in self.UNITS:
            raise TypeError("Invalid unit name.")

        self.name = name

    def __eq__(self, o):
        try:
            return self.name == o.name
        except AttributeError:
            return self.name == o

    def __lt__(self, o):
        try:
            return is_subunit(self.name, o.name)
        except AttributeError:
            return is_subunit(self.name, o)

    def __gt__(self, o):
        try:
            return is_superunit(self.name, o.name)
        except AttributeError:
            return is_superunit(self.name, o)

    def __le__(self, o):
        if self == o:
            return True
        return self < o

    def __ge__(self, o):
        if self == o:
            return True

        return self > o


class CalendarPeriod:
    """ A period of time as a collection of units of time.

    CalendarPeriod is a period with a start, end, and duration
    and is iterable over smaller units of time within it.
    It is built to model the way people think of periods of time.
    To see what role it plays, we will define the terms
    terms: 'period', 'label', and 'moment.'
    A 'moment' is an instance in time to which a specific 'label' can be applied.
    The label 'January 1, 2022,' can refer to the very instance that day begins.
    Since python usually uses microseconds as it's smallest unit of time, we will
    then consider that label to be shorthand for 'January 1, 2022 00:00:00.000000'.
    Alternatively, the label 'January 1, 2022' can also refer to the period
    that includes all of the moments of time from January 1, 2022 to
    just before January 2, 2022. In this case we think of that label as being
    shorthand for all of the microseconds from
    January 1, 2022 00:00:00.000000 to January 1, 2022, 23:59:59.999999.
    CalendarPeriod repsesents this sort of time, while we use traditional
    datetime objects to represent moments.

    Any usnits of time not specified are assumed to be zero.
    To specify the 20th minute of the 4th hour of January 1, 2022 set:
    start to January 1, 2022 04:20.
    """

    @property
    def end(self):
        return self._end

    def __init__(self, start, end=None, duration=None, name=None):
        """
        Parameters:
            start: a date or datetime representing the first moment in time for this period.
            end:
                a date or datetime referring to end refers to the beginning
                moment of the next period of time.
                For instance setting 'start' to Dec 31, 2000 and 'last' to Jan 1, 2001
                would make the CelandarPeriod represent all microseconds from Dec 31, 2000 tor
                to one microsecond before Jan 1, 2001.
            last: a date or datetime represent int the last period in time for this period.
        """
        if not isinstance(start, datetime):
            start = datetime.combine(start, time())
        self.start = start

        if end is not None:
            if not isinstance(end, datetime):
                end = datetime.combine(end, time())
            if end <= start:
                raise TypeError("end must be after start.")
            self._end = end
        elif duration is not None:
            self._last = self.start + duration

        else:

        if name is not None:
            self.name = name


if pytest is not False:
    class Test_TUnit:
        def test_init(self):
            with pytest.raises(TypeError):
                u = TUnit("monkey")
            assert TUnit("second").name == "second"

        def test_comp(self):
            hour = TUnit("hour")
            minute = TUnit("minute")
            assert hour > minute
            assert not (hour < minute)
            assert hour >= minute
            hour2 = TUnit("hour")
            assert hour == hour2
            assert hour >= hour2
            assert hour <= hour2

            assert hour == "hour"
            assert hour > "second"
            assert not (hour < "second")
