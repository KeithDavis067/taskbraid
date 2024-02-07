import calendar
from datetime import datetime, timedelta, date, time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from calendar import monthrange, month_name, day_name
try:
    import pandas as pd
except ImportError:
    pass

# TODO: Figure out how to import pytest only when testing.
try:
    import pytest
except ImportError:
    pass

# TODO: Add event class. Recase Year_Data as and "event" class and add make
# Year_Data a subclass.


def get_duration(obj):
    if obj._duration is not None:
        return obj._duration
    try:
        return obj.end - obj.start
    except TypeError:
        return None


def set_duration(obj, value):
    # Throw error if we don't act like a delta.
    if value is None:
        del obj.duration
    else:
        value + datetime(2000, 1, 1)
        # Enforce internal duration storage.
        obj._duration = value
        if obj._start is not None:
            obj._end = None
        elif obj._end is not None:
            obj._start = None


def get_start(obj):
    if obj._start is not None:
        return obj._start

    try:
        return obj._end - obj._duration
    except TypeError:
        return None


def set_start(obj, value):
    if value is None:
        del obj.start
    else:
        obj._start = value
        if obj._end is not None:
            obj._duration = None


def del_start(obj):
    if obj._duration is None:
        obj._duration = obj._end - obj._start
    obj._start = None


def get_end(obj):
    if obj._end is not None:
        return obj._end

    try:
        return obj._start + obj._duration
    except TypeError:
        return None


def set_end(obj, value):
    if value is None:
        del obj.end
    else:
        obj._end = value
        if obj._start is not None:
            obj._duration = None


def del_end(obj):
    if obj._duration is None:
        obj._duration = obj._end - obj._start
    obj._end = None


class CalendarElement:

    ABSUNITS = ["year",
                "month",
                "day",
                "hour",
                "minute",
                "second",
                "microsecond"]

    RELUNITS = [a + 's' for a in ABSUNITS]

    @classmethod
    def set_rd_props(cls):
        for u in cls.ABSUNITS:
            setattr(cls, u, property(lambda self,
                    u=u: getattr(self.relativedelta, u)))

    @property
    def unit(self):
        sm = None
        for u in self.ABSUNITS:
            if getattr(self.relativedelta, u) is not None:
                sm = u
        return sm

    @property
    def subunits(self):
        idx = self.__class__.ABSUNITS.index(self.unit)
        return self.__class__.ABSUNITS[idx + 1:]

    def __init__(self, **kwargs):
        if any([k not in self.__class__.ABSUNITS for k in kwargs]):
            raise TypeError("Element units must be one of: "
                            f"{self.__class__.ABSUNITS}")

        self.relativedelta = relativedelta(**kwargs)
        self._set_ranges()

    def _set_ranges(self):
        self.unitranges = {}
        for u in self.__class__.ABSUNITS:
            try:
                self.unitranges[u] = range(
                    getattr(self, u), getattr(self, u) + 1)
            except TypeError:
                self.unitranges[u] = None
        for u in self.unitranges:
            if self.unitranges[u] is None:
                match u:
                    case "year":
                        self.unitranges[u] = None
                    case "day":
                        try:
                            self.unitranges[u] = range(
                                1, monthrange(self.year, self.month)[1]+1)
                        except TypeError:
                            if self.year is None:
                                if self.month == 2 or self.month is None:
                                    raise ValueError(
                                        "February may occur during iteration."
                                        "Set year to determine number of days.")
                            # Defer setting to iteration code.
                            self.unitranges[u] = None
                    case "month":
                        self.unitranges[u] = range(1, 13)
                    case "minute" | "second":
                        self.unitranges[u] = range(1, 60)
                    case "hour":
                        self.unitranges[u] = range(1, 23)
                    case "microsecond":
                        self.unitranges[u] = range(1, 1000000)

    def __len__(self):
        total = 1
        for u in self.unitranges:
            if self.unitranges[u] is not None:
                total *= len(self.unitranges[u])

    def iterover(self, unit=None, units=None, date=False, tuple=False, value=None):
        # TODO: Rewrite this to handle iterating over subunit when higher unit is not set.
        if value is None:
            value = self.relativedelta
        if unit is not None:
            units = [unit]

        unit = units[0]
        for unit in units:
            if unit != "day":
                for i in self.unitranges[unit]:
                    setattr(value, unit, i)
                    yield i
                    yield from self.iterover(units=units[1:], date=date, value=value)
            else:
                for i in range(1, monthrange(value.year, value.month)[1]+1):
                    setattr(value, unit, i)
                    yield i
                    yield from self.iterover(units=units[1:], date=False, value=value)

    def iter(self):
        yield from self.iterover()


CalendarElement.set_rd_props()


def _quacks_like_a_dt(obj):
    """ Reusable function to allow passing dt objects or parseable strings."""
    try:
        obj.date()
        obj.year
        obj.day
        obj.month
        obj + timedelta(1)
    except (AttributeError, TypeError):
        return False
    return True


def test_quacks_like_a_dt():
    assert _quacks_like_a_dt(datetime(2020, 1, 1))
    assert not _quacks_like_a_dt(None)
    assert not _quacks_like_a_dt(date(2020, 1, 1))
    assert not _quacks_like_a_dt("2020-01-01")

    assert _quacks_like_a_dt(_fakedt())


def _quacks_like_a_time(obj):
    try:
        obj.minute
        obj.hour
    except AttributeError:
        return False

    try:
        obj.day
        obj.month
        obj.year
    except AttributeError:
        pass
    else:
        return False
    return True


def test_quacks_like_a_time():
    assert _quacks_like_a_time(time(0, 0, 0))
    assert not _quacks_like_a_time(timedelta(days=1))
    assert not _quacks_like_a_time(datetime.now())
    assert not _quacks_like_a_time(date.today())


def _quacks_like_a_date(obj):
    try:
        obj.year
        obj.day
        obj.month
        obj + timedelta(1)
    except (AttributeError, TypeError):
        return False

    try:
        obj.date()
        return False
    except AttributeError:
        pass
    return True

    assert _quacks_like_a_date(_fakedate())


class _fakedt:
    """ For testing only. """

    def __init__(self):
        self.year = None
        self.day = None
        self.month = None
        self.minute = None
        self.second = None
        self.microsecond = None

    def __radd__(self, other):
        pass

    def __add__(self, other):
        pass

    def date(self):
        pass


class _fakedate:
    """ For testing only. """

    def __init__(self):
        self.year = None
        self.day = None
        self.month = None

    def __radd__(self, other):
        pass

    def __add__(self, other):
        pass


def test_quacks_like_a_date():
    assert _quacks_like_a_date(date(2020, 1, 1))
    assert _quacks_like_a_date(datetime(2020, 1, 1).date())
    assert not _quacks_like_a_date(None)
    assert not _quacks_like_a_date(datetime(2020, 1, 1))
    assert not _quacks_like_a_date("2020-01-01")


def _chrono_kind(obj):
    if _quacks_like_a_date(obj):
        return "date"

    if _quacks_like_a_dt(obj):
        return "dt"

    if _quacks_like_a_time(obj):
        return "time"

    raise TypeError(
        f"{obj} is used as a chrono type but does not quack like one.")


def test_chrono_kind():
    assert _chrono_kind(date(2020, 1, 1)) == "date"
    assert _chrono_kind(datetime(2020, 1, 1)) == "dt"

    assert _chrono_kind(_fakedate()) == "date"
    assert _chrono_kind(_fakedt()) == "dt"

    with pytest.raises(TypeError):
        _chrono_kind(1)
    with pytest.raises(TypeError):
        _chrono_kind("2020-01-01")


def _date_setter(obj, value, attr="date"):
    # _date_or_dt will raise error if neither.
    kind = _chrono_kind(obj)
    match kind:
        case "date":
            setattr(obj, attr, value)
        case "dt":
            # To mathc gcsa implementation, set as date if time is
            # exactly zero.
            # This might trash timezone data on dates, so if
            # not local tz we might
            # leave time, but I need to read more about tzinfo first.
            if (dt.hours,
                dt.minutes,
                dt.seconds,
                    dt.microseconds) == (0, 0, 0, 0):
                setattr(obj, attr, value.date())
            else:
                setattr(obj, attr, value)


def _validate_date_input(value, start=None, end=None, inc="days"):
    """ Verifies a value as a date or integer with increment.

    If start and end are passed, verified that value is within the range
    [start, end). If one but not both are None, only compare to set value(s).
    If value is inc, then `start` must be set. The date returned will be
    a number of `inc` increments added to `start`.

    No attempt is made to similarly coerce start/end to dates.

    """
    out_of_range = "{date} is in not given range: {start} to {end}"
    try:
        kind = _chrono_kind(value)
        date = value
    except TypeError:
        if inc in [days, seconds, microseconds,
                   milliseconds, minutes, hours, weeks]:
            kwarg = {inc: value}
            date = start + timedelta(**kwarg)
        raise ValueError(f"{value} is not a date and cannot be "
                         "coerced to a date with given parameters.")

    if start is not None:
        if not start <= date:
            raise outofrange.format(**locals())

    if end is not None:
        if not date < end:
            raise outofrange.format(**locals())
    return date


class Event:
    """
    Implementation Note: gcsa module gets events from gcal with the start date as expected
    and the end as the moment the event ends. So, a single date events starts on the day it
    starts and ends the next day. Also, events without times are stored as datetime.dates, while
    events with a time are stored as datetime.datetime objects.

    We will adopt this structure for simplicity's sake. This matters mostly for the __timecontains__
    function. That will be implemented so that it returns True if event.start <= datetime < event.end.
    This means for an event that lasts one day, the next date will not return True, but one microsecond
    before. A meeting event that lasts from 10:00 AM to 11:00 AM will return False on the call:
        `11:00 AM in event`.
    """
    @ property
    def start(self):
        return self._start

    @ start.setter
    def start(self, value):
        _date_setter(obj, value, "start")

    @ property
    def end(self):
        return self._end

    @ end.setter
    def start(self, value):
        _date_setter(obj, value, "end")


class Year_Data():

    @ property
    def year(self):
        return self._year

    @ year.setter
    def year(self, year):
        try:
            if self.date.year != year:
                self._year = year
            del self.date
        except (AttributeError, TypeError):
            pass

        self._year = year

    @ property
    def date(self):
        if self._date is None:
            return datetime.date(self.year, 1, 1)
        return self._date

    @ date.setter
    def date(self, date):
        _date_setter(self, date, "date")

    @ date.deleter
    def date(self):
        self._date = None

    @ property
    def start(self):
        return date(self.year, 1, 1)

    @ property
    def end(self):
        return date(self.year + 1, 1, 1)

    def __init__(self, year=None, date=None):
        if year is None:
            year = datetime.now().year
        self.year = year

        if date is None:
            date = datetime(self.year, 1, 1)
        self.date = date

    def length(self):
        """ Return the length of the calendar year in days."""
        return (self.end - self.start).days

    def weekday(self, n=None):
        if n is None:
            return self.date.weekday()
        else:
            return self.number_as_date(n).weekday()

    def number_as_date(self, n, unit="days"):
        """ Return the date from an integer (Jan 1 = 0)."""
        return self.start() + timedelta(days=n)

    def date_as_number(self, d=None):
        if d is None:
            d = self.date

        try:
            return (d - self.start().date()).days
        except TypeError:
            return (d.date() - self.start().date()).days

    def monthrange(self, month=None):
        if month is None:
            month = self.date.month
        return monthrange(self.year, month)

    def iterdates(self, start=0, end=None):

        if end is None:
            end = self.end

        if end not in self:
            if end != self.end:
                raise (
                    ValueError, f"{end} is not in calendar year {self.year}.")

        # If start is an int, create a date from it.
        try:
            start = self.number_as_date(start)
        except TypeError:
            # If not an int, it may be datetime.
            pass
        try:
            if not _date_contains(self.start, start, end):
                raise ValueError(
                    f"{start} is not in calendar year {self.year}.")
        except TypeError as e:
            if not (self.start().date() <= start.date() < end.date()):
                raise TypeError(
                    "start must be a number, or quack like a date or datetime.")
        while start in self:
            yield start
            start += day

    def __contains__(self, value):
        try:
            return self.start() <= value < datetime(self.year+1, 1, 1)
        except TypeError:
            try:
                return self.start().date() <= value < datetime(self.year+1, 1, 1).date()
            except TypeError:
                return self.start() <= self.number_as_date(value) <= datetime(self.year+1, 1, 1)

    def to_dict(self):
        columns = ["date", "year", "month", "month_str",
                   "day", "weekday", "weekday_str"]
        funcs = [lambda d: d,
                 lambda d: d.year,
                 lambda d: d.month,
                 lambda d: month_name[d.month],
                 lambda d: d.day,
                 lambda d: d.weekday(),
                 lambda d: day_name[d.weekday()]]
        col_func = dict(zip(columns, funcs))

        year_dict = {}
        for column in columns:
            year_dict[column] = []

        for date in self.iterdates():
            for column in col_func:
                year_dict[column].append(col_func[column](date))

        return year_dict

    def to_DataFrame(self):
        try:
            return pd.DataFrame(self.to_dict())
        except (NameError, UnboundLocalError):
            raise ModuleNotFoundError("pandas is not installed.")

    def __len__(self):
        return self.length().days
