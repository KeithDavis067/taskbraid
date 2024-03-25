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


RANGES = {"year": range(date.min.year, date.max.year + 1),
          "month": range(1, 13),
          "day": None,
          "hour": range(0, 24),
          "minute": range(0, 60),
          "second": range(0, 60),
          "microsecond": range(0, 1000000)}

UNITS = list(RANGES.keys())


def _subunit(unit):
    if unit == "microsecond":
        return None
    return UNITS[UNITS.index(unit) + 1]


def _superunit(unit):
    if unit == "year":
        return None
    return UNITS[UNITS.index(unit) - 1]


class TimeDigit:
    value = property(lambda self: getattr(self, "_value"),
                     lambda self, value: _set_value(self, value))

    @ property
    def superunit(self):
        """ Return superunit object or string."""
        if self._superunit is not None:
            return self._superunit
        if self.unit == "year":
            return None
        return _superunit(self.unit)

    @superunit.setter
    def superunit(self, value):
        """ Set superunit object."""
        try:
            if value.unit == _superunit(self.unit):
                self._superunit = value
            else:
                raise ValueError(f"Incorrect superunit for '{
                                 self.unit}' object.")
        except AttributeError:
            if (value == _superunit(self.unit)) or (value is None):
                self._superunit = None
            else:
                raise ValueError(f"Incorrect superunit for '{
                                 self.unit}' object.")

    @superunit.deleter
    def superunit(self):
        self._superunit = None

    @property
    def subunit(self):
        try:
            if self._subunit is None:
                return _subunit(self.unit)
        except AttributeError:
            self._subunit = None
            return self.subunit
        return self._subunit

    @subunit.setter
    def subunit(self, value):
        try:
            if value.unit == _subunit(self.unit):
                if isinstance(value.superunit, str):
                    value.superunit = self
                elif value.superunit is not self:
                    raise ValueError(f"Value superunit '{value.superunit}' is not self '{self}'."
                                     "Set value superunit to self before assigning.")
                self._subunit = value
            else:
                raise ValueError(f"Incorrect subunit for '{
                                 self.unit}' object.")
        except AttributeError:
            if (value == _subunit(self.unit)) or (value is None):
                self._subunit = None
            else:
                raise ValueError(f"Incorrect subunit for '{
                                 self.unit}' object.")

    @subunit.deleter
    def subunit(self):
        self._subunit = None

    def __init__(self, unit, value=None, superunit=None, subunit=None):
        if unit not in UNITS:
            raise TypeError(f"{unit} not one of {UNITS}.")
        self.unit = unit
        self.superunit = superunit
        self.subunit = subunit
        _set_range(self)
        self.value = value

    def __getattr__(self, name):
        try:
            steps = UNITS.index(name) - UNITS.index(self.unit)
        except ValueError:
            raise AttributeError(
                f"'{self.__class__}' has no attribute '{name}'")

        su = self
        while (steps > 0) and (not isinstance(su, str)):
            su = su.subunit
            steps = steps - 1

        while (steps < 0) and (not isinstance(su, str)):
            su = su.superunit
            steps = steps + 1
        if not isinstance(su, str):
            return su.value

        raise AttributeError(
            f"'{self.__class__}' has no attribute '{name}'. Set sub/superunit "
            "attribute to define implicit sub/superunits.")

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.itr)
        except (AttributeError, TypeError):
            self.itr = iter(self.range)
            return next(self.itr)

    def as_dict(self):
        d = {"type": type(self),
             "unit": self.unit,
             "value": self.value,
             "subunit": self.subunit}
        return d

    def __repr__(self):
        return str(self.as_dict())


def _walk(obj, upordown, func):
    su = obj
    res = []
    while su is not None:
        res.append(func(su))
        try:
            match upordown:
                case "up":
                    su = su.superunit
                case "down":
                    su = su.subunit
        except (AttributeError, TypeError):
            su = None

    return res


class CalendarElement(TimeDigit):
    @property
    def element(self):
        def retv(su):
            try:
                v = self.value
            except AttributeError:
                v = None
        return v

        up = _walk(self, "up", lambda su: return (su.unit, su.value))
        down = _walk(self, "down", lambda su: return (su.unit, su.value))
        try:
            for

    def __init__(self, **kwargs):
        params = {}
        for k in ["unit", "value", "subunit", "superunit"]:
            try:
                params[k] = kwargs.pop(k)
            except KeyError:
                params[k] = None

        if (params["unit"] is not None) and (params["value"] is None):
            try:
                params["value"] = kwargs.pop(params["unit"])
            except KeyError:
                pass

        if params["unit"] is None:
            for u in UNITS:
                try:
                    params["value"] = kwargs.pop(u)
                    params["unit"] = u
                    break
                except KeyError:
                    pass

        super().__init__(params.pop("unit"), **params)

        if isinstance(self.subunit, str):
            try:
                self.subunit = self.__class__(superunit=self, **kwargs)
            except TypeError:
                pass

    def __next__(self):
        try:
            # If we're already iterating on subunit.
            self.subunit.value = next(self.subunit.itr)
        except AttributeError:
            try:
                # If we have a subunit, but aren't iterating.
                self.subunit.itr = iter(self.subunit.range)
                self.subunit.value = next(self.subunit.itr)
            except AttributeError:
                # If our subunit is not an instance, but the string.
                self.subunit = self.__class__(
                    unit=self.subunit, superunit=self)
                self.subunit.itr = iter(self.subunit.range)
                self.subunit.value = next(self.subunit.itr)

        except TypeError as e:
            # If subunit is None.
            raise TypeError(
                f"{self.unit} has no subunit over which to iterate.") from e

        return self.subunit

    def __iter__(self):
        return self

    def __len__(self):
        try:
            return len(self.subunit.range)
        except (AttributeError, TypeError):
            return len(self.__class__(unit=self.subunit, superunit=self).range)


def _set_range(obj):
    obj.range = RANGES[obj.unit]

    if obj.unit == "day":
        try:
            month = obj.superunit.month
        except (AttributeError, TypeError):
            raise ValueError(
                "Cannot set range for days if month is not available.")
        if month == 2:
            print(month)
            try:
                year = obj.superunit.superunit.year
                print(year)
            except (AttributeError, TypeError):
                raise ValueError(
                    "Cannot set range for February if year is not available.")
        else:
            year = 1999
        obj.range = range(1, monthrange(year, month)[1]+1)


def _set_value(obj, value):
    if (value not in obj.range) and (value is not None):
        raise ValueError(f"{value} not in {obj.unit} of {obj.superunit}")
    obj._value = value


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
            if (obj.hours, obj.minutes,
                    obj.seconds, obj.microseconds) == (0, 0, 0, 0):
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
        if inc in ["days",
                   "seconds", "microseconds",
                   "minutes", "hours", "weeks"]:
            kwarg = {inc: value}
            date = start + timedelta(**kwarg)
            raise ValueError(f"{value} is not a date and cannot be "
                             "coerced to a date with given parameters.")

    if start is not None:
        if not start <= date:
            raise out_of_range.format(**locals())

        if end is not None:
            if not date < end:
                raise out_of_range.format(**locals())
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
        _date_setter(self, value, "start")

    @ property
    def end(self):
        return self._end

    @ end.setter
    def start(self, value):
        _date_setter(self, value, "end")
