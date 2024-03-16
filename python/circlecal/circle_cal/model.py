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

    DATEUNITS = ABSUNITS[0:3]
    TIMEUNITS = ABSUNITS[3:]

    UNITORDER = dict([(u, i) for i, u in enumerate(reversed(ABSUNITS))])

    @property
    def unit(self):
        sm = None
        for u in self.ABSUNITS:
            try:
                if getattr(self, u) is not None:
                    sm = u
            except AttributeError:
                pass
        return sm

    @ property
    def subunits(self):
        idx = self.__class__.ABSUNITS.index(self.unit)
        try:
            return self.__class__.ABSUNITS[idx + 1:]
        except IndexError:
            return None

    @ property
    def superunits(self):
        idx = self.__class__.ABSUNITS.index(self.unit)
        try:
            return self.__class__.ABSUNITS[:idx]
        except IndexError:
            return None

    @property
    def subunit(self):
        su = self.subunits
        if su is None:
            return None
        if len(su) == 0:
            return None
        return su[0]

    def __init__(self, **kwargs):
        if any([k not in self.__class__.ABSUNITS for k in kwargs]):
            raise TypeError("Element units must be one of: "
                            f"{self.__class__.ABSUNITS}")

        for u in self.ABSUNITS:
            try:
                setattr(self, u, kwargs[u])
            except KeyError:
                setattr(self, u, None)

        self._set_ranges()

    def range(self, range):
        return self.ranges[self.subunit]

    def _set_ranges(self):
        self.ranges = {}
        ulist = [self.unit]
        if self.subunit is not None:
            ulist = ulist + [self.subunit]

        for u in ulist:
            try:
                self.ranges[u] = range(
                    getattr(self, u), getattr(self, u) + 1)
            except (TypeError, AttributeError):
                self.ranges[u] = None
        for u in self.ranges:
            if self.ranges[u] is None:
                match u:
                    case "year":
                        self.ranges[u] = None
                    case "day":
                        try:
                            self.ranges[u] = range(
                                1, monthrange(self.year, self.month)[1]+1)
                        except TypeError:
                            if self.year is None:
                                if self.month == 2 or self.month is None:
                                    raise ValueError(
                                        "February may occur during iteration."
                                        "Set year to determine number of days.")
                                else:
                                    self.ranges[u] = range(
                                        1, monthrange(2000, self.month)[1]+1)
                            # Defer setting to iteration code.
                            else:
                                raise ValueError("Cannot determine number of "
                                                 "days if month is not set.")
                    case "month":
                        self.ranges[u] = range(1, 13)
                    case "minute" | "second":
                        self.ranges[u] = range(0, 60)
                    case "hour":
                        self.ranges[u] = range(0, 24)
                    case "microsecond":
                        self.ranges[u] = range(0, 1000000)

    @ property
    def value(self):
        if self.superunits is not None:
            units = self.superunits + [self.unit]
        else:
            units = [self.unit]
        return dict((u, getattr(self, u)) for u in units)

    def __iter__(self):
        try:
            for i in self.ranges[self.subunit]:
                v = self.value
                v[self.subunit] = i
                yield self.__class__(**v)
        except KeyError:
            pass

    def recursive_iter(self, maxdepth=3, depth=None):
        if depth is None:
            depth = 0
        else:
            depth = depth + 1
        if depth >= maxdepth:
            yield self
        else:
            for sub in self:
                yield from sub.recursive_iter(maxdepth=maxdepth, depth=depth)

    def __len__(self):
        return len(list(self.__iter__()))

    def as_dict(self):
        return dict(zip(self.ABSUNITS, [getattr(self, u) for u in self.ABSUNITS]))

    def __str__(self):
        return str(self.asdict)

    def date(self):
        """ Return a date object representing the date of this object.

        If object does not have a defined year, day, and month raises TypeError.

        """
        return date(**dict([(u, v) for u, v in self.as_dict().items() if
                            u in self.DATEUNITS]))

    def time(self):
        """ Return a time object representing the time of this object.

        If no time is stored, will return time object called with no values:
        `time()`
        """
        return time(**dict([(u, v) for u, v in self.as_dict().items() if
                            ((v is not None) and (v in self.TIMEUNITS))]
                           )
                    )

    def datetime(self):
        return datetime.combine(self.date(), self.time())

    def has_time(self):
        if any([getattr(self, u) is not None for u in self.TIMEUNITS]):
            return True
        return False

    def has_date(self):
        if any([getattr(self, u) is not None for u in self.DATEUNITS]):
            return True
        return False


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
            if (dt.hours, dt.minutes,
                    dt.seconds, dt.microseconds) == (0, 0, 0, 0):
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
        if inc in [days, seconds, microseconds, milliseconds, minutes, hours, weeks]:
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
