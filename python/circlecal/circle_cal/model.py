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


def _set_unit_range(obj):
    obj.unit_range = RANGES[obj.unit]

    if obj.unit == "day":
        try:
            month = obj.superunit.month
        except (AttributeError, TypeError):
            raise ValueError(
                "Cannot set range for days if month is not available.")
        if month == 2:
            try:
                year = obj.superunit.superunit.year
            except (AttributeError, TypeError):
                raise ValueError(
                    "Cannot set range for February if year is not available.")
        else:
            year = 1999
        obj.unit_range = range(1, monthrange(year, month)[1]+1)


def _get_value(obj):
    return obj._value


def _set_value(obj, value):
    if (value not in obj.unit_range) and (value is not None):
        raise ValueError(f"{value} not in {obj.unit} of {obj.superunit}")
    obj._value = value


# TODO: CHange around some definitions, value_range is the full range or the value to value + 1 range.
# value returns the actual value or None.
# unit_range returns the possible range for the unit (with the correct choice of 28, 29, 30 or 31 days.)
#


class TimeDigit:
    """ A digit that keeps track of super and sub time units.

    """
    value = property(lambda self: _get_value(self),
                     lambda self, value: _set_value(self, value),
                     lambda self: _set_value(self, None))

    def value_range(obj):
        """ Return a range object taking into account the current value.

        If `value` is set, return a range object from `value` to `value+1`.
        Otherwise return a range object for the whole range of `unit`.
        """
        try:
            return range(obj._value, obj._value+1)
        except TypeError:
            return range(obj.unit_range)

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
        """ Set superunit object.

        Checks that superunit object has the correct units before assignment.
        """
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
        """ Remove superunit object.

        Ensures no reference to another object as a superunit.
        Calls to the `superunit` attribute will still return a string value for the unit.
        """
        self._superunit = None

    @property
    def subunit(self):
        """ Return a reference to a subunit object or string."""
        try:
            if self._subunit is None:
                return _subunit(self.unit)
        except AttributeError:
            self._subunit = None
            return self.subunit
        return self._subunit

    @subunit.setter
    def subunit(self, obj):
        """ Ensure param `obj` is the correct subunit and set the attribute."""
        try:
            if obj.unit == _subunit(self.unit):
                if isinstance(obj.superunit, str):
                    obj.superunit = self
                elif obj.superunit is not self:
                    raise ValueError("'superunit' attribute on param 'obj'"
                                     "must be unassigned or this instance.")
                self._subunit = obj
            else:
                raise ValueError(
                    f"Incorrect subunit for '{self.unit}' object.")
        except AttributeError:
            if (obj == _subunit(self.unit)) or (obj is None):
                self._subunit = None
            else:
                raise ValueError(f"Incorrect subunit for "
                                 f"'{self.unit}' object.")

    @subunit.deleter
    def subunit(self):
        """ Remove subunit object.

        Ensures no reference to another object as a subunit.
        Calls to the `subunit` attribute will still return a string value for the unit.
        """
        self._subunit = None

    def __init__(self, unit, value=None, superunit=None, subunit=None):
        """ TimeDigit constructor.

        Parameters:
            unit: a string from the list `UNITS`.
        Keywords:
            value: None or a number for the value of the unit.
            superunit: None or a TimeDigit object with the correct unit
                one step greater than `unit`.
            subunit: None or a TimeDigit object with the correct unit
                one step smaller than `unit`.
        """
        if unit not in UNITS:
            raise TypeError(f"{unit} not one of {UNITS}.")
        self.unit = unit
        self.superunit = superunit
        self.subunit = subunit
        _set_unit_range(self)
        self.value = value

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.itr)
        except (AttributeError, TypeError):
            self.itr = iter(self.value)
            return next(self.itr)

    def as_dict(self):
        d = {"type": type(self),
             "unit": self.unit,
             "value": self.value,
             "subunit": self.subunit,
             "superunit": self.superunit}
        return d

    def __repr__(self):
        return str(self.as_dict())

    def __str__(self):
        if len(self.value_range) == 1:
            match self.unit:
                case "year":
                    s = f"{self.value:04}"
                case _:
                    s = f"{self.value:02}"
        return " ".joint(s + [s.unit, "s"])


def _walk(obj, upordown, func):
    res = []
    su = obj
    while su is not None:
        try:
            match upordown:
                case "up":
                    su = su.superunit
                case "down":
                    su = su.subunit
        except (AttributeError, TypeError):
            su = None
        try:
            res.append(func(su))
        except AttributeError:
            break
    return res


def _retv(su):
    try:
        v = su.value
    except AttributeError:
        v = None

    return (su.unit, v)


class CalendarElement:
    """ A span of time described as a unit part of a particular date and or time.

    A CalendarElement represents a span of time referred to by a unit. 
    WHen superunit and subunit attributes are assigned to other instances,
    the combined set of CalendarElements refers a specific unit of time.
    Iteration returns a CalendarElement for the direct division of that unit,
    and `len` returns the length of those units.

    Consider a CalendarElement of unit `year` with the value `2024`:
    Without any other assignment, this refers to the span of time that is the
    year 2024. let `y = CalendarElement('year', 2024)` then len(y) returns 12, for
    the 12 months of 2024, and y.subunit returns the string "month".

    By linking a set of CalendarElement instances via assignment to subunits or superunits,
    a specific date or time can be described. In the previous example, also
    let `m` = CalendarElement('month', value=1, superunit=y) and 
    y.superunit = m.
    Then y and m specify February of 2024, and the length will be properly set as 29 days.

    """
    @ property
    def get_element(self):
        """ Return the largest unit with a specified value.

        The string identifying unit the collection of linked CalendarElement instances
        represent.
        For instance, if super or sub units of the year, month, and day are
        assigned values, then on the element attribute of all of these elements
        will return 'day'.
        """
        raise NotImplementedError()

    def __init__(self, **kwargs):
        """ Initiliase a CalendarElement, automatically assiging subunits if included in kwargs.

        """
        for u in UNITS:
            if u in kwargs:
                print(u, kwargs)
                setattr(self, u, kwargs[u])

    @property
    def unit(self):
        for u in UNITS:
            try:
                if getattr(self, u) is not None:
                    continue
            except (AttributeError):
                break
        return u

    def subunit(self):
        try:
            return UNITS[UNITS.index(self.unit) + 1]
        except IndexError:
            return None

    def as_dict(self):
        d = {}
        for u in UNITS:
            try:
                d[u] = getattr(self, u).value
            except AttributeError:
                pass
        return d

    def __iter__(self):
        d = self.as_dict()
        try:
            d[self._state.unit] = next(self._state)
        except AttributeError:
            state = TimeDigit(self.subunit, value=None,
                              superunit=getattr(self, self.unit.unit))
            self._state = state
        yield self.__class__(**d)


print("Setting, monkeys.")
for u in UNITS:
    print("Applying", u)
    setattr(CalendarElement, u, property(lambda obj: get_unit_digit(obj, u),
            lambda obj, value: set_unit_digit(obj, u, value),
            lambda obj: setattr(obj, u, None)))


def get_unit_digit(obj, u):
    print(u)
    try:
        return getattr(obj, "_" + u)
    except AttributeError as e:
        raise AttributeError(
            f"{obj.__class__} instance has no attribute {u}") from e


def set_unit_digit(obj, u, value):
    print(u, value)
    # Try to set the value of the timedigit.
    try:
        getattr(obj, u).value = value
    # If no timedigit, then if value may be a timedigit.
    except AttributeError:
        try:
            if value.unit == u:
                setattr(obj, "_" + u, value)
            else:
                raise ValueError(f"{value} unit does not match {u}")
        except AttributeError:
            try:
                setattr(obj, "_" + u, TimeDigit(u, value,
                        superunit=getattr(obj, UNITS[UNITS.index(u)-1])))
            except (IndexError, AttributeError):
                setattr(obj, "_" + u, TimeDigit(u, value))


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
