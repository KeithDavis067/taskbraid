import calendar
from datetime import datetime, timedelta, date, time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from calendar import monthrange, month_name, day_name
from collections import namedtuple

__all__ = ["CalendarElement", "TimeDigit"]
try:
    import pandas as pd
except ImportError:
    pass

# TODO: Figure out how to import pytest only when testing.
try:
    import pytest
except ImportError:
    pass


def get_duration(obj):
    if obj._duration is not None:
        return obj._duration
    try:
        return obj.stop - obj.start
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
            obj._stop = None
        elif obj._stop is not None:
            obj._start = None


def get_start(obj):
    if obj._start is not None:
        return obj._start

    try:
        return obj._stop - obj._duration
    except TypeError:
        return None


def set_start(obj, value):
    if value is None:
        del obj.start
    else:
        obj._start = value
        if obj._stop is not None:
            obj._duration = None


def del_start(obj):
    if obj._duration is None:
        obj._duration = obj._stop - obj._start
    obj._start = None


def get_stop(obj):
    if obj._stop is not None:
        return obj._stop

    try:
        return obj._start + obj._duration
    except TypeError:
        return None


def set_stop(obj, value):
    if value is None:
        del obj.stop
    else:
        obj._stop = value
        if obj._start is not None:
            obj._duration = None


def del_stop(obj):
    if obj._duration is None:
        obj._duration = obj._stop - obj._start
    obj._end = None


# Start CalendeElement Material
RANGES = {"year": range(date.min.year, date.max.year + 1),
          "month": range(1, 13),
          "day": None,
          "hour": range(0, 24),
          "minute": range(0, 60),
          "second": range(0, 60),
          "microsecond": range(0, 1000000)}

UNITS = list(RANGES.keys())

# UTrip = namedtuple(["superunit", "unit", "subunit"])
# UNITS = []
# for i, u in enumerate(RANGES):
#     try:
#         sub = list(RANGES.keys())[i+1]
#     except IndexError:
#         sub = None
#     try:
#         sup = list(RANGES.keys())[i-1]
#     except IndexError:
#         sup = None
#     UNITS.append(UTrip(sup, u, sub))


def _subunit(unit):
    if unit == UNITS[-1]:
        return None
    return UNITS[UNITS.index(unit) + 1]


def test_subunit():
    assert _subunit("year") == "month"
    assert _subunit("microsecond") is None


def _subunits(unit):
    if unit == UNITS[-1]:
        return []
    return UNITS[UNITS.index(unit) + 1:]


def test_subunits():
    assert _subunits("second") == ["microsecond"]
    assert _subunits("minute") == ["second", "microsecond"]
    assert _subunits("microsecond") == []


def _superunit(unit):
    if unit == UNITS[0]:
        return None
    return UNITS[UNITS.index(unit) - 1]


def test_superunit():
    assert _superunit("year") is None
    assert _superunit("microsecond") == "second"


def _superunits(unit):
    if unit == UNITS[0]:
        return []
    ru = list(reversed(UNITS))
    return ru[ru.index(unit) + 1:]


def test_superunits():
    assert _superunits("month") == ["year"]
    assert _superunits("day") == ["month", "year"]
    assert _superunits("year") == []


def _unit_range(obj):
    if obj.unit == "day":
        try:
            month = obj.superunit.month
        except (AttributeError, TypeError):
            raise ValueError(
                "Cannot set range for days if month is not available.")
        if month is None:
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
        return range(1, monthrange(year, month)[1]+1)
    return RANGES[obj.unit]


def _get_value(obj):
    return obj._value


def _set_value(obj, value):
    if value == "start":
        value = obj.unit_range.start
    if value in ["stop", "end"]:
        value = obj.unit_range.stop

    if (value not in obj.unit_range) and (value is not None):
        raise ValueError(f"{value} not in {obj.unit} of {obj.superunit}")
    obj._value = value


class TimeDigit:
    """ A digit for a unit of time, that is aware of greater and smaller units.

    """
    value = property(lambda self: _get_value(self),
                     lambda self, value: _set_value(self, value),
                     lambda self: _set_value(self, None))

    @ property
    def superunit(self):
        """ Return superunit object or string."""
        try:
            if self._superunit is not None:
                return self._superunit
            else:
                return _superunit(self.unit)
        except AttributeError:
            return _superunit(self.unit)

    @superunit.setter
    def superunit(self, obj):
        """ Set superunit object.

        Checks that superunit object has the correct units before assignment.
        """
        try:
            if obj.unit == _superunit(self.unit):
                if isinstance(obj.subunit, str):
                    obj._subunit = self
                elif obj.subunit is not self:
                    raise ValueError("'subunit' attribute on param 'obj'"
                                     "must be unassigned or this instance.")
                self._superunit = obj
            else:
                raise ValueError(
                    f"Incorrect superunit for '{self.unit}' object.")
        except AttributeError:
            if (obj == _superunit(self.unit)) or (obj is None):
                self._superunit = None
            else:
                raise ValueError(f"Incorrect superunit for "
                                 f"'{self.unit}' object.")

    @superunit.deleter
    def superunit(self):
        """ Remove superunit object.

        Ensures no reference to another object as a superunit.
        Calls to the `superunit` attribute will still return a string
        of the unit value or None.
        or None.
        """
        self._superunit = None

    @property
    def subunit(self):
        """ Return a reference to a subunit object or string."""
        try:
            if self._subunit is not None:
                return self._subunit
            else:
                return _subunit(self.unit)
        except AttributeError:
            return _subunit(self.unit)

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

    @property
    def start(self):
        return self.range.start

    def stop(self):
        return self.range.stop

    def __getattr__(self, name):
        if name == self.unit:
            return self.value
        return self.__getattribute__(name)

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
        self.unit_range = _unit_range(self)
        self.range = self.unit_range
        self.value = value

    def __iter__(self):
        return self

    def __next__(self):
        try:
            if self.value is None:
                v = self.range.start
            else:
                v = self.value + 1
        except AttributeError:
            v = self.range.start
        try:
            self.value = v
        except ValueError:
            try:
                next(self.superunit)
                self.value = self.range.start
            except ValueError:
                raise StopIteration
        return self.value

    def as_dict(self):
        d = {"type": type(self),
             "unit": self.unit,
             "value": self.value,
             "subunit": self.subunit,
             "superunit": self.superunit}
        return d

    def __repr__(self):
        d = self.as_dict()
        # This avoids infinite recursion.
        if not isinstance(d["superunit"], str):
            d["superunit"] = object.__repr__(self.superunit)
        if not isinstance(d["subunit"], str):
            d["subunit"] = object.__repr__(self.subunit)
        return str(d)

    def __str__(self):
        try:
            if self.value is None:
                v = self.start
            else:
                v = self.value
        except AttributeError:
            v = self.start

        match self.unit:
            case "year":
                s = f"{v:04}"
            case _:
                s = f"{v:02}"
        return s

    def __eq__(self, other):
        """ Return True if unit and value match. """
        if self.unit != other.unit:
            return False
        if self.value != other.value:
            return False
        return True

    def __len__(self):
        try:
            return self.value - self.start
        except (AttributeError, TypeError):
            return self.stop - self.start


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


def _setunitattr(obj, name, value):
    if name in UNITS:
        obj.set_unit(name, value)
    else:
        object.__setattr__(obj, name, value)


def _getunitattr(obj, name):
    try:
        return obj.get_unit(name)
    except KeyError:
        pass

    obj.__getattribute__(name)


def _delunitattr(obj, name):
    if name in obj.digits:
        del obj.digits[name]
    else:
        object.__delattr__(obj, name)


class TimeRegister:
    __getattr__ = _getunitattr
    __setattr__ = _setunitattr
    __delattr__ = _delunitattr

    def __init__(self, **kwargs):
        self.digits = {}
        for u in UNITS:
            if u in kwargs:
                try:
                    self.digits[u] = TimeDigit(
                        u, kwargs[u], superunit=self.digits[_superunit(u)])
                except KeyError:
                    self.digits[u] = TimeDigit(u, kwargs[u])
            else:
                if (any([un in self.digits.keys() for un in _superunits(u)]) and
                        any([un in kwargs for un in _subunits(u)])):
                    self.digits[u] = TimeDigit(
                        u, value="start", superunit=self.digits[_superunit(u)])

    def get_unit(self, u):
        return self.digits[u]

    def datetime(self):
        rd = relativedelta(**self.as_dict())
        d = date(1, 1, 1)
        return d + rd

    def __iter__(self):
        return self

    def __next__(self):
        units = list(self.digits.keys())
        next(self.digits[units[-1]])
        return self

    def as_dict(self):
        d = dict()
        for u in self.digits:
            d[u] = self.digits[u].value
        return d

    def __str__(self):
        return str(self.datetime())


class CalendarElement:
    """ A span of time described as a unit part of a date and or time.

    A CalendarElement represents a unit of time that can be placed on a
    calendar.
    Iteration returns a CalendarElement for the direct division of that unit,
    and `len` returns the number of those units in this element.

    Consider a CalendarElement of unit `year` with the vngealue `2024`:
    Without any other assignment, this refers to the span of time that is the
    year 2024. let `y = CalendarElement('year', 2024)` then len(y) returns 12, for
    the 12 months of 2024, and y.tsubunit returns the string "month".

    For any unit with an assigned value, it will have a TimeDigit object
    accessible by the get_digit_by_unit attribute. The above CalendarElement
    with the year value assigned as 2024 will have a TimeDigit assiged
    the unit `year` and value `2024`. The TimeDigit instances keep track
    of what value each unit has been assigned, and what values are possible
    given other unit values. So a CalendarElement with the `year` assigned as
    `2024` and the month assigned as `2` for February, will "know" that the
    allowed day values are 1-29. It will raise an error if an attempt is made to
    assign the day to 30, for example.

    Iteration returns


    """

    RANGES = RANGES
    UNITS = UNITS

    @ property
    def unit(self):
        """ Return the unit this instance represents.

        If the top level is not set then return "none".
        """
        # If we hit a None return the previous unit.
        # If not, then we must be at "microsecond."
        # If year isn't set, we will return None.
        for u in UNITS:
            try:
                if self.digits[u] is None:
                    raise KeyError
            except KeyError:
                return _superunit(u)
        return "microsecond"

    @ property
    def digit(self):
        """ Return the TimeDigit object for self.unit."""
        if self.unit is None:
            return None
        return getattr(self, self.unit)

    @ digit.setter
    def digit(self, value):
        setattr(self, self.unit, value)

    @ digit.deleter
    def digit(self):
        delattr(self, self.unit)

    @ property
    def value(self):
        return self.digit.value

    @ value.setter
    def value(self, value):
        self.digit.value = value

    @ property
    def subunit(self):
        """ Return string representing subunit or None if no subunits."""
        return _subunit(self.unit)

    def subunits(self): return _subunits(self.unit)

    @ property
    def superunit(self):
        return _superunit(self.unit)

    def superunits(self): return _superunits(self.unit)

    def set_unit(self, unit, value):
        """ Set a value or a TimeDigit to a unit.

        Implementation note: This function accesses unit
        attributes directly, not through getattr. All other
        methods use setattr when assigning which is passed to this
        method.

        """
        # If we're doing a delete operation.
        if value is None:
            for u in [unit] + _subunits(unit):
                del self.digits[unit]
            try:
                self.digits[_superunit(u)].subunit = None
            except (AttributeError, KeyError):
                pass
        # If we're setting a value.
        else:
            try:
                # Timedigits must match the unit we're assigning to.
                if value.unit == unit:
                    v = value.value
                else:
                    raise TypeError("value unit must match unit string.")
            # Catch if we have no unit attr.
            except AttributeError:
                v = value

            # If we aren't at "year".
            if _superunit(unit) is not None:
                # IF we're setting a value without setting all the in between first.
                try:
                    if self.digits[_superunit(unit)].value is None:
                        raise KeyError
                except (KeyError, TypeError):
                    dt = self.datetime() + relativedelta(**{unit + "s": v})
                    print(unit)
                    for u in _superunits(unit):
                        try:
                            self.set_unit(u, getattr(dt, u))
                        except AttributeError:
                            self.set_unit(u, 0)
                    # IF we've set it this way we're done.
                    return
                # If we aren't at "year" but have all inbetween units set.
                td = TimeDigit(unit, value=v,
                               superunit=self.digits[_superunit(unit)])
            else:
                td = TimeDigit(unit, value=v)

        if td.subunit is not None:
            try:
                self.digits[_subunit(unit)].superunit = td
                td.subunit = self.digits[_subunit(unit)]
            except KeyError:
                pass
        self.digits[unit] = td

    def get_unit(self, u):
        return self.digits[u]

    __getattr__ = _getunitattr
    __setattr__ = _setunitattr
    __delattr__ = _delunitattr

    def __init__(self, **kwargs):
        """ Initiliase with values from unit kwargs.

        """
        self.digits = {}
        for u in UNITS:
            try:
                self.set_unit(u, kwargs[u])
            except KeyError:
                # Do nothing if no value passed for u.
                continue

    def as_dict(self):
        d = {}
        for u in UNITS:
            try:
                d[u] = getattr(self, u).value
            except AttributeError:
                pass
        return d

    def gen_sub_digit(self, value=None):
        return TimeDigit(self.subunit, value=value, superunit=self.digit)

    def gen_sub_element(self, value=None):
        d = self.as_dict()
        d[self.subunit] = self.gen_sub_digit(value=value).range.start
        return self.__class__(**d, superunit=self.digit)

    def __getitem__(self, i):
        if self.subunit is None:
            raise TypeError(f"{self.unit} has no members.")

        # This lets us get the start range for the unit.
        new = self.gen_sub_element()
        try:
            if i >= 0:
                new.value = new.range.start + i
            else:
                new.value = new.range.stop + i
        except ValueError as e:
            raise IndexError from e

        return new

    def datetime(self):
        rd = relativedelta(**self.as_dict())
        d = datetime(1, 1, 1)
        return d + rd

    def __len__(self):
        try:
            # return llen(TimeDigit(self.subunit, superunit=getattr(self, self.unit)))en(TimeDigit(self.subunit, superunit=getattr(self, self.unit)))
            return len(self.gen_sub_digit().range)
        except TypeError as e:
            raise TypeError(
                f"Cannot create smaller elements for {self}") from e

    def recursive_iteration(self, unit):
        if UNITS[UNITS.index(unit)] > UNITS[UNITS.index(self.unit)]:
            raise ValueError(f"{unit} not a subunit of {self.unit}")

        for sub in self:
            if sub.unit == unit:
                yield sub
            else:
                yield from sub.recursive_iteration(unit)

    @ property
    def range(self):
        return getattr(self, self.unit).range

    @ property
    def subunit_range(self):
        if self.subunit is None:
            return None
        return TimeDigit(self.unit, superunit=self).range

    @ property
    def start(self):
        new = self.__class__(**self.as_dict())
        if new.unit != UNITS[-1]:
            new.digits[self.subunit] = TimeDigit(
                self.subunit, "start", superunit=new.digits[self.unit])
        return new

    @ property
    def stop(self):
        tr = TimeRegister(**self.as_dict())
        tr = next(tr)
        return CalendarElement(**tr.as_dict())

    def __repr__(self):
        d = self.as_dict()
        d["type"] = "CalendarElement"
        return str(d)

    def date_to_unit(self, d, unit="days"):
        dt = self.start.datetime() - d
        return dt / timedelta(**{unit: 1})

    def __lt__(self, other):
        # Since stop is one us greater than final moment, include eq.
        try:
            return self.stop.datetime() <= other.start.datetime()
        except AttributeError:
            return self.stop.datetime() <= other

    def __le__(self, other):
        # If less than then we're true but lt rules.
        if self < other:
            return True
        else:
            return self == other

    def __ge__(self, other):
        # If less than then we're true but lt rules.
        if self > other:
            return True
        else:
            return self == other

    def __gt__(self, other):
        try:
            return self.start.datetime() >= other.stop.datetime()
        except AttributeError:
            return self.start.datetime() > other

    def __eq__(self, other):
        try:
            return self.datetime() == other.datetime()
        except AttributeError:
            return self.datetime() == other

    def __contains__(self, other):
        # If we have no subunits, then we don't know about smaller units.
        print("Contains Called.")
        if self.subunit is None:
            return False
        # Can we make a subunit?
        try:
            if self.subunit == other.unit:
                try:
                    self.gen_sub_element(other.value)
                    return True
                except ValueError:
                    return False
            else:
                return False
        except (AttributeError, TypeError):
            return self.start <= other < self.stop


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
            if (obj.hours,
                obj.minutes,
                obj.seconds,
                    obj.microseconds) == (0, 0, 0, 0):
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
