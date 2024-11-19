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


def day_range(obj):
    try:
        return range(1, monthrange(obj.year, obj.month)[1] + 1)
    except (AttributeError, TypeError):
        return None


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


class DTPrecision:
    UNITS = UNITS
    RANGES = RANGES

    @property
    def ranges(self):
        r = self.RANGES.copy()
        r["day"] = day_range(self)
        return r

    def __getattr__(self, name):
        if name in UNITS:
            return None
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in UNITS:
            # If this is None, all lower values
            # should be cleared to None.
            if value is None:
                for u in [name] + _subunits(name):
                    super().__setattr__(u, None)
                return

            # Ensure all superunits are set to
            # a value or set them to their start.
            old = self.to_dict()
            su = _superunit(name)
            try:
                if getattr(self, su) is None:
                    try:
                        setattr(self, su, self.ranges[su].start)
                    # If month has no value, set to one. This should trigger
                    # setting month.
                    except AttributeError:
                        setattr(self, su, 1)
            # If we're at the top of the list of units.
            except TypeError:
                pass
            # Now set this value, if day, month should be set and ranges
            # should return a a range for the month.
            if value in self.ranges[name]:
                super().__setattr__(name, value)
            else:
                for u, v in old.items():
                    super().__setattr__(u, v)
                raise ValueError(f"{value} not in range for {name}")

        super().__setattr__(name, value)

    def __init__(self, **kwargs):
        for u in self.UNITS:
            try:
                v = kwargs.pop(u)
                setattr(self, u, v)
            except KeyError:
                pass

    def to_dict(self):
        return dict([(u, getattr(self, u)) for u in self.UNITS])


class Test_DTPrecision:
    def test_to_dict(self):
        dtp = DTPrecision()
        assert dtp.to_dict() == dict([(u, None) for u in UNITS])

    def test_init(self):
        dtp = DTPrecision(year=2024)
        assert dtp.year == 2024
        assert dtp.minute is None
        dtp = DTPrecision(year=2024, day=1, minute=20)
        assert dtp.year == 2024
        assert dtp.day == 1
        assert dtp.minute == 20


class TUnit:
    UNITS = UNITS

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
    def start(self):
        # Holding start as unmodifiable after creation for now.
        # May edit when modifying stop and end automatically
        # is implemented.
        return self._start

    @property
    def stop(self):
        """ The first moment of the next time period.
        Stop is the first moment that is definitely in another time period.
        Analogous to 'stop' in range objects, the item can iterate to this moment
        but should not return it.
        """
        return self._stop

    @property
    def end(self):
        """ The last microsecond of this period.
        """
        return self.stop - timedelta(microseconds=1)

    def __init__(self, start, stop=None, end=None, duration=None, name=None):
        """
        Parameters:
            start: a date or datetime representing the first moment in time for this period.
            stop:
                a date or datetime referring to end refers to the beginning
                moment of the next period of time.
                For instance setting 'start' to Dec 31, 2000 and 'last' to Jan 1, 2001
                would make the CelandarPeriod represent all microseconds from Dec 31, 2000 tor
                to one microsecond before Jan 1, 2001.
            last: a date or datetime represent int the last period in time for this period.
        """
        pass
        # if not isinstance(start, datetime):
        #     start = datetime.combine(start, time())
        # self._start = start
        #
        # if stop is not None:
        #     if not isinstance(stop, datetime):
        #         end = datetime.combine(stop, time())
        #     if stop <= start:
        #         raise TypeError("end must be after start.")
        #     self._stop = stop
        # elif duration is not None:
        #     self._last = self.start + duration
        #
        # else:
        #
        # if name is not None:
        #     self.name = name


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


class whole_unit_tester:
    def __init__(start, end):
        self.start = start
        self.end = end


def whole_unit(obj):
    if is_whole_years(obj):
        return "years"

    if is_whole_months(obj):
        return "months"

    td = obj.last - obj.start

    for u in TD_UNITS:
        if td_is_zero(td % timedelta(**{u: 1})):
            return u
    return u


def _any_smaller_unit_is_nonzero(obj, unit):
    for u in _subunits(unit):
        try:
            if getattr(obj, u) != 0:
                return True
        except AttributeError:
            pass
    return False


def is_whole_months(obj):
    if obj.start.day != 1:
        return False

    if obj.end.day != monthrange(obj.last.year, obj.last.month)[1]:
        return False

    if _any_smaller_unit_is_nonzero(obj.start, "day"):
        return False

    if _any_smaller_unit_is_nonzero(obj.last, "day"):
        return False

    return True


def is_whole_years(obj):
    if obj.end.year < obj.start.year:
        return False

    if obj.start.month != 1:
        return False

    if obj.start.day != 1:
        return False

    if obj.end.month != 12:
        return False

    if obj.end.day != 31:
        return False

    if _any_smaller_unit_is_nonzero(obj.start, "day"):
        return False

    if _any_smaller_unit_is_nonzero(obj.end, "day"):
        return False

    return True


def _zero_list(obj):
    i = 0
    while _any_smaller_unit_is_nonzero(obj, UNITS[i]):
        i += 1
    return UNITS[i:]


def _n_u(obj, u=None):
    wu = whole_unit(obj)
    if u is None:
        u = wu
    else:
        if u[0:-1] not in [wu[0:-1]] + _subunits(wu[0:-1]):
            raise ValueError(
                f"unit '{u}' is larger than whole unit '{wu}' of period.")
    match u:
        case "years":
            return obj.last.year - obj.start.year + 1

        case "months":
            return obj.last.month - obj.start.month + 1
        case _:
            return obj.duration / timedelta(**{u: 1})


def item_unit(obj):
    wu = whole_unit(obj)
    if _n_u(obj, wu) == 1:
        return _subunit(wu[0:-1]) + "s"
    else:
        return wu


def datelike_to_dict(dt):
    d = {}
    for u in UNITS:
        try:
            d[u] = getattr(dt, u)
        except AttributeError:
            pass
    return d


def datelike_to_end(obj):
    d = datelike_to_dict(obj)
    for u in reversed(UNITS):
        zu = u
        if d[u] != 0:
            break
    for u in _subunits(zu):
        if u is None:
            return obj
        if u == "month":
            d[u] = monthrange(obj.year, obj.month)[1]
        else:
            d[u] = RANGES[u][-1]
    return datetime(**d)


def test_datelike_to_end():
    dt = datetime(2000, 1, 1)
    assert datelike_to_end(dt) == datetime(2000, 1, 1, 23, 59, 59, 999999)
    dt = datetime(2000, 12, 1, 23, 59, 59, 999999)
    assert datelike_to_end(dt) == datetime(2000, 12, 1, 23, 59, 59, 999999)
