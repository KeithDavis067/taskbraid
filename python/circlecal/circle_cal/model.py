import calendar
from datetime import datetime, timedelta, date, time
from dateutil.parser import parse
from datetutil.relativedelta import relativedelta
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
#


class Period:

    @property
    def duration(self):
        if self._duration is not None:
            return self._duration
        try:
            return self.end - self.start
        except TypeError:
            return None

    @duration.setter
    def duration(self, value):
        # Throw error if we don't act like a delta.
        if value is None:
            del self.duration
        else:
            value + datetime(2000, 1, 1)
            # Enforce internal duration storage.
            self._duration = value
            if self._start is not None:
                self._end = None
            elif self._end is not None:
                self._start = None

    @property
    def start(self):
        if self._start is not None:
            return self._start

        try:
            return self._end - self._duration
        except TypeError:
            return None

    @start.setter
    def start(self, value):
        if value is None:
            del self.start
        else:
            self._start = value
            if self._end is not None:
                self._duration = None

    @start.deleter
    def start(self):
        if self._duration is None:
            self._duration = self._end - self._start
        self._start = None

    @property
    def end(self):
        if self._end is not None:
            return self._end

        try:
            return self._start + self._duration
        except TypeError:
            return None

    @end.setter
    def end(self, value):
        if value is None:
            del self.end
        else:
            self._end = value
            if self._start is not None:
                self._duration = None

    @end.deleter
    def end(self):
        if self._duration is None:
            self._duration = self._end - self._start
        self._end = None

    def __init__(start=None, end=None, duration=None):
        if all([p is None for p in locals().values()]):
            raise TypeError("Must pass start and end or duration.")

        if duration is None:
            if start is None or end is None:
                raise TypeError(
                    "If duration is not set, both start and end must be set.")

        self._duration = None
        self._start = None
        self._end = None

        self.duration = duration
        self.start = start
        self.end = end


def _quacks_like_a_dt(obj):
    """ Reusable function to allow passing dt objects or parseable strings."""
    try:
        obj.date()
        obj.year
        obj.day
        obj.hour
        obj.month
        obj.minute
        obj.second
        obj.microsecond
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
        obj.second
        obj.microsecond
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


def test_date_or_dt():
    assert _date_or_dt(date(2020, 1, 1)) == "date"
    assert _date_or_dt(datetime(2020, 1, 1)) == "dt"

    assert _date_or_dt(_fakedate()) == "date"
    assert _date_or_dt(_fakedt()) == "dt"

    with pytest.raises(TypeError):
        _date_or_dt(1)
    with pytest.raises(TypeError):
        _date_or_dt("2020-01-01")


def _chrono_contains(start, value, end):
    """ return true if value is in the timespan [start, end) false otherwise.

    Return True if `value` is in the timespan described by `start` and `end`.
    Evaluation can be complicated, but the following is designed to answer
    the simple "human-like" version of the question: is the moment in time referred to by
    `value` between `start` and `end` or does it occur on a date referred to by `start` and
    `end if they represent a single day. True if yes, False if no.

    If all parameters are the same object type, comparison uses the builtin
    comparison rules.

    For mixed types, dates without times in the `start` position refer to the first moment
    of that date while dates in the `end` position refer to the last moment of that date.
    So if start regers to "January 1, 2000" it is treated as January 1, 2000 00:00.0 and
    January 1, 2000 in the `end` position is treated as January 1, 2000 23:59.00.
    (To arbitrary precision when possible.)
    Times without dates are treated as wall-clock times. If that time can occur
    within the range return True, otherwise return False.

    Example: `start` is a datetime representing january 1, 2000 at 10:00 am
             `end` is a date object representing january 1, 2000.
             Since `start` is a datetime `end` is interpreted as the last
             moment before the change over to Jan 2, 2000.
             if `value` is 10:00 am return True. (bevause start <= value).
             if `value` is 8:00 am  return False, because the clock time of
             8:00 am does not occur between jan 1, 2000 10:00 and the last moment
             of January 1, 2000.

            `
            _chrono_contains(datetime(2000, 1, 1, 10, 0),
                              10:00,
                              date(2000, 1, 1))
            -> True
            `


    If both `start` and `end` are dates, and value is a time, then return True as long as
    start <= end. The rationale is: any time without a date refers to the whole day, unless
    another datetime (or time) cuts off part of the day.
    """
    # My insistence on duck-typing might be pathological.

    # If it works, it works.
    try:
        return start <= value < end
    except TypeError:
        pass

    pattern = [_chrono_kind(start), _chrono_kind(value), _chrono_kind(end)]

    match pattern:
        case ["dt", "time", "dt"]:
            if start.time() <= value < (datetime.combine(datetime(2000, 1, 1)) - time.resolution).time():
                value = datetime.combine(start.date(), value)
                return start <= value < end

        case ["dt", "date", "dt"]:
            return start <= datetime.combine(value, time(0, 0)) < end

        case ["dt", "date", "date"]:
            return start <= datetime.combine(value, time(0, 0)) < datetime.combine(end, time(0, 0) - timedelta.resolution)


def test_chrono_contains():
    # TODO: Finish this.
    assert _chrono_contains(datetime(2000, 1, 1),
                            time(10, 0),
                            datetime(2000, 1, 1))

    assert _chrono_contains(datetime(2000, 1, 1),
                            datetime(2000, 1, 1),
                            datetime(2000, 1, 1))

    assert _chrono_contains(datetime(2000, 1, 1),



def _date_setter(obj, value, attr="date"):
    # _date_or_dt will raise error if neither.
    kind=_date_or_dt(obj)
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
    out_of_range="{date} is in not given range: {start} to {end}"
    try:
        kind=_date_or_dt(value)
        date=value
    except TypeError:
        if inc in [days, seconds, microseconds,
                   milliseconds, minutes, hours, weeks]:
            kwarg={inc: value}
            date=start + timedelta(**kwarg)
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
                self._year=year
            del self.date
        except (AttributeError, TypeError):
            pass

        self._year=year

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
        self._date=None

    @ property
    def start(self):
        return date(self.year, 1, 1)

    @ property
    def end(self):
        return date(self.year + 1, 1, 1)

    def __init__(self, year=None, date=None):
        if year is None:
            year=datetime.now().year
        self.year=year

        if date is None:
            date=datetime(self.year, 1, 1)
        self.date=date

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
            d=self.date

        try:
            return (d - self.start().date()).days
        except TypeError:
            return (d.date() - self.start().date()).days

    def monthrange(self, month=None):
        if month is None:
            month=self.date.month
        return monthrange(self.year, month)

    def iterdates(self, start=0, end=None):

        if end is None:
            end=self.end

        if end not in self:
            if end != self.end:
                raise (
                    ValueError, f"{end} is not in calendar year {self.year}.")

        # If start is an int, create a date from it.
        try:
            start=self.number_as_date(start)
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
        columns=["date", "year", "month", "month_str",
                   "day", "weekday", "weekday_str"]
        funcs=[lambda d: d,
                 lambda d: d.year,
                 lambda d: d.month,
                 lambda d: month_name[d.month],
                 lambda d: d.day,
                 lambda d: d.weekday(),
                 lambda d: day_name[d.weekday()]]
        col_func=dict(zip(columns, funcs))

        year_dict={}
        for column in columns:
            year_dict[column]=[]

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
