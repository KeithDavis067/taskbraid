import calendar
from datetime import datetime, timedelta, date, time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from calendar import monthrange, month_name, day_name
from collections import namedtuple
from workalendar.usa import UnitedStates, Indiana
from pytz import timezone


ETZ = timezone("America/New_York")

try:
    from skyfield.api import load
    from skyfield import almanac
    skyfield = True
except ImportError:
    skyfield = False

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


def is_subunit(left, right):
    if left in _subunits(right):
        return True
    return False


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


def mid(obj):
    match _chrono_kind(obj.start):
        case "date":
            return datetime.combine(obj.start, time(0, 0)) + (obj.duration / 2)
        case "dt":
            return obj.start + (obj.duration / 2)
        case "time":
            secs = obj.start.hour * 3600 + \
                obj.start.minute * 60, + \
                obj.start.second + obj.start.microsecond / 1e6
            td = obj.duration / 2 + timedelta(seconds=secs)
            if td < 24 * 60 * 60:
                return time(0, 0) + td
            else:
                raise ValueError(
                    "Cannot return midpoint longer than one day from "
                    "events without known date.")


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
                    raise ValueError(f"'subunit' attribute on param 'obj'"
                                     f"is {obj.subunit}"
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

    return obj.__getattribute__(name)


def _delunitattr(obj, name):
    if name in obj.digits:
        setattr(obj, name, None)
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

    def subunits(self):
        return _subunits(self.unit)

    @ property
    def superunit(self):
        return _superunit(self.unit)

    def superunits(self):
        return _superunits(self.unit)

    @property
    def name(self):
        if self.unit == "month":
            try:
                return calendar.month_name[self.value]
            except TypeError:
                return None
        else:
            return str(self.value)

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
                try:
                    del self.digits[u]
                except KeyError:
                    pass
            try:
                self.digits[_superunit(unit)].subunit = None
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
                    if getattr(self, _superunit(unit)) is None:
                        raise AttributeError
                except AttributeError:
                    self.set_unit(_superunit(unit), "start")
                td = TimeDigit(
                    unit, value=v, superunit=self.digits[_superunit(unit)])

            else:
                # we are at 'year.'
                td = TimeDigit(unit, value=v)

            self.digits[unit] = td

    def get_unit(self, u):
        return self.digits[u]

    __getattr__ = _getunitattr
    __setattr__ = _setunitattr
    __delattr__ = _delunitattr

    def __init__(self, label=None, **kwargs):
        """ Initiliase with values from unit kwargs.

        """
        self.label = label
        self.digits = {}
        for u in UNITS:
            try:
                try:
                    # Fist kwarg may be date, time or datetime..
                    self.set_unit(u, getattr(
                        kwargs[list(kwargs.keys())[0]], u))
                except AttributeError:
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
        # Creating on a copy so that we don't assign this digit
        # as a subdigit of self.
        new = CalendarElement(**self.as_dict())
        return TimeDigit(new.subunit, value=value, superunit=new.digit)

    def gen_sub_element(self, value=None):
        d = self.as_dict()
        d[self.subunit] = self.gen_sub_digit(value=value).range.start
        return CalendarElement(**d)

    @property
    def duration(self):
        return self.stop.datetime() - self.start.datetime()

    @property
    def mid(self):
        return self.start.datetime() + (self.duration / 2)

    def __getitem__(self, i):
        if self.subunit is None:
            raise TypeError(f"{self.unit} has no members.")

        try:
            r = range(i.start, i.stop, i.step)
        except TypeError:
            try:
                r = range(i.start, i.stop)
            except AttributeError:
                r = [i]
        except AttributeError:
            r = [i]

        # This lets us get the start range for the unit.
        result = []

        for i in r:
            new = self.gen_sub_element()
            try:
                if i >= 0:
                    new.value = new.range.start + i
                else:
                    new.value = new.range.stop + i
            except ValueError as e:
                raise IndexError from e
            result.append(new)

        if hasattr(r, "start"):
            return result
        else:
            return result[0]

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

    def subunit_generator(self, unit):
        # if UNITS.index(unit) > UNITS.index(self.unit):
        #     raise ValueError(f"{unit} not a subunit of {self.unit}")
        if unit not in self.subunits():
            raise ValueError(f"{unit} not a subunit of {self.unit}")

        for sub in self:
            if sub.unit == unit:
                yield sub
            else:
                yield from sub.subunit_generator(unit)

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
        new = CalendarElement(**self.as_dict())
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
        td = timedelta(seconds=(to_timestamp(d) -
                                self.start.datetime().timestamp()))
        return td / timedelta(**{unit: 1})

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


class Event:
    @ property
    def duration(self):
        try:
            if self._duration is not None:
                return self._duration
        except AttributeError:
            pass
        dur = self._end - self.start
        if dur == timedelta(0):
            dur = self.combine(self._end, time(0, 0, 0)) - self.start
        return dur

    @ duration.setter
    def duration(self, value):
        try:
            if self._end is not None:
                del self._end
        except AttributeError:
            pass
        self._duration = value

    @ property
    def end(self):
        try:
            if self._end is not None:
                return self._end
        except AttributeError:
            return self.start + self._duration

    @ end.setter
    def end(self, value):
        try:
            if self._duration is not None:
                del self._duration
        except AttributeError:
            pass
        self._end = value

    def __str__(self):
        try:
            if self.label is not None:
                return f"({self.label}: {self.start} to {self.end})"
        except AttributeError:
            pass
        return f"Event: {self.start} to {self.end}"

    __repr__ = __str__

    @ property
    def mid(self):
        mid = self.start + (self.duration / 2)
        if mid == self.start:
            mid = datetime.combine(self.start,
                                   time(0, 0, 0)) + (self.duration / 2)
        return mid

    def __init__(self, start, **kwargs):
        self.start = start
        try:
            self.duration = kwargs["duration"]
        except KeyError:
            pass

        try:
            self.end = kwargs["end"]
        except KeyError:
            pass

        try:
            self.mid
        except AttributeError as e:
            raise TypeError(
                "Cannot initialize without one of keywords 'duration' or 'end'.") from e

        try:
            self.label = kwargs["label"]
        except KeyError:
            self.label = None

        # Below is convenience for calling label, summary whem mixed in with gcale eventrs.
        @property
        def summary(self):
            return self.label

        @summary.setter
        def summary(self, value):
            self.label = value


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
            if (obj.hours, obj.minutes, obj.seconds, obj.microseconds) == (0, 0, 0, 0):
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


class EventWrap:
    """
    Implementation Note: gcsa module gets events from gcal with the start date as expected
    and the end as the moment the event ends. So, a single date events starts on the day it
    starts and ends the next day. Also, events without times are stored as datetime.dates, while
    events with a time are stored as datetime.datetime objects.

    We will adopt this structure for simplicity's sake. This matters mostly for the __timecontains__
    function. That will be implemented so that it returns True if event.start <= datetime < event.end.
    This means for an evenet that lasts one day, the next date will not return True, but one microsecond
    before. A meeting event that lasts from 10:00 AM to 11:00 AM will return False on the call:
        `11:00 AM in event`.
    """

    def __init__(self, gcsaevent):
        if isinstance(gcsaevent, self.__class__):
            self.gcsaevent = gcsaevent.gcsaevent
        else:
            self.gcsaevent = gcsaevent

    @ property
    def duration(self):
        return timedelta(seconds=(to_timestamp(self.end) - to_timestamp(self.start)))

    mid = property(mid)

    def __getattr__(self, name):
        try:
            return getattr(self.gcsaevent, name)
        except AttributeError:
            pass
        return self.__getattribute__(name)

    def __setattr__(self, name, value):
        if name == "gcsaevent":
            object.__setattr__(self, name, value)
        setattr(self.gcsaevent, name, value)


def to_timestamp(obj):
    try:
        ts = obj.timestamp()
    except AttributeError:
        ts = datetime.combine(obj, time(0, 0)).timestamp()
    return ts


def year_to_sunburst(year):
    y = CalendarElement(year=year)
    parents = [None]
    names = [y.year.value]
    values = [1]
    for m in y:
        parents.append(y.year.value)
        names.append(m.name)
        values.append(1)
        for day in m:
            parents.append(m.name)
            names.append(f"{day.year}-{day.month}-{day.day}")
            values.append(1)
    return dict(parents=parents,
                labels=names, values=values)


yd = year_to_sunburst(2024)


def localize_any(obj, tz):
    try:
        return tz.localize(obj)
    except ValueError:
        if obj.tzinfo:
            return obj
    except AttributeError:
        return tz.localize(datetime.combine(obj, time(0, 0)))
    return obj


def weekday(datelike):
    return list(calendar.day_name)[calendar.weekday(datelike.year,
                                                    datelike.month,
                                                    datelike.day)]


def is_weekend(datelike):
    if calendar.weekday(datelike.year, datelike.month, datelike.day) in [5, 6]:
        return True
    else:
        return False


def weekends(yearlike):
    try:
        g = iter(yearlike)
    except AttributeError:
        try:
            g = Year(yearlike.year).subunit_generator("day")
        except AttributeError:
            g = Year(yearlike).subunit_generator("day")

    ws = []
    start = None
    for d in CalendarElement(year=2024).subunit_generator("day"):
        d = d.datetime()
        if is_weekend(d):
            if start is None:
                start = d
            else:
                ws.append(Event(start, end=d))
                start = None
    return ws


def season_events(obj):
    try:
        year = obj.year
    except AttributeError:
        year = obj

    if skyfield:
        ts = load.timescale()
        eph = load('de421.bsp')
        t0 = ts.utc(year, 1, 1)
        t1 = ts.utc(year, 12, 31)
        t, y = almanac.find_discrete(t0, t1, almanac.seasons(eph))
        dates = []
        for yi, ti in zip(y, t):
            dates.append(Event(start=datetime.fromisoformat(ti.utc_iso(' ')),
                               duration=timedelta(seconds=2),
                               label=almanac.SEASON_EVENTS_NEUTRAL[yi]))
    else:
        june = date(year, 6, 21)
        december = date(year, 12, 21)
        march = date(year, 3, 21)
        september = date(year, 9, 21)
        dates = [Event(june, duration=timedelta(days=1), label="June Solstice"),
                 Event(december, duration=timedelta(
                     days=1), label="December Solstice"),
                 Event(march, duration=timedelta(
                     days=1), label="March Solstice"),
                 Event(september, duration=timedelta(
                     days=1), label="September Solstice"),
                 ]

    return dates


class NotreDame(Indiana):
    include_easter_monday = True
    include_good_friday = True
    include_easter_sunday = True
    include_christmas_eve = True


def whole_unit(obj):
    if is_whole_years(obj):
        return "years"

    if is_whole_months(obj):
        return "months"

    td = obj.end - obj.start

    for u in TD_UNITS:
        if td_is_zero(td % timedelta(**{u: 1})):
            return u
    return u


def is_whole_months(obj):
    if obj.start.day != 1:
        return False

    if obj.end.day != monthrange(obj.end.year, obj.end.month)[1]:
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

    return True


def _n_u(obj, u=None):
    wu = whole_unit(obj)
    if u is None:
        u = wu
    else:
        if u not in [wu] + _subunits(wu[0:-1]):
            raise ValueError(
                f"unit '{u}' is larger than whole unit '{wu}' of period.")
    match u:
        case "years":
            return obj.end.year - obj.start.year + 1

        case "months":
            return obj.end.month - obj.start.month + 1
        case _:
            return obj.duration / timedelta(**{u: 1})


def _iterate_months(obj, start, stop, step):
    months = obj.end.month - obj.start.month
    if start > months:
        raise IndexError

    begin_month = obj.start
    # If start is not 0, add months until we are at th start-th month
    # from obj.start.
    for j in range(obj.start.month, obj.start.month + start):
        begin_month += timedelta(
            days=monthrange(begin_month.year, j)[1])
    months = []
    for j in range(begin_month.month, begin_month.month + 1, step):
        start_date = datetime(year=begin_month.year,
                              month=begin_month.month,
                              day=begin_month.day)
        end_date = datetime(year=begin_month.year,
                            month=begin_month.month,
                            day=monthrange(begin_month.year,
                                           begin_month.month)[1])
        months.append(CalendarPeriod(start=start_date, end=end_date,
                                     name=month_name[begin_month.month]))
    if start == stop:
        return months[0]
    else:
        return months


def datelike_to_dict(dt):
    d = {}
    for u in UNITS:
        try:
            d[u] = getattr(dt, u)
        except AttributeError:
            pass
    return d


class CalendarPeriod:
    @property
    def duration(self):
        return self.end - self.start

    whole_unit = whole_unit

    def __len__(self):
        return _n_u(self)

    def __init__(self, start, end=None, duration=None, name=None):
        if not isinstance(start, datetime):
            start = datetime.combine(start, time())
        self.start = start

        if end is not None:
            if not isinstance(end, datetime):
                end = datetime.combine(start, time())

            self.end = end

        else:
            try:
                self.end = self.start + duration
            except TypeError as e:
                raise TypeError("One of keywords 'start' "
                                "or 'duration' must be set.") from e

        if name is not None:
            self.name = name

    def __getitem__(self, i):
        try:
            start = i.start
        except AttributeError:
            start = i

        try:
            if i.stop is None:
                stop = start
            else:
                stop = i.stop
        except AttributeError:
            stop = start + 1

        try:
            if i.step is None:
                step = 1
            else:
                step = i.step
        except AttributeError:
            step = 1

        stop = stop + step

        wu = self.whole_unit()
        if _n_u(self, wu) == 1:
            wu = _subunit(wu[0:-1]) + "s"

        items = []
        for j in range(start, stop, step):
            if wu == "years":
                year = self.start.year + j
                start_date = datetime(year, 1, 1)
                end_date = datetime(year, 12, 31)
                name = str(year)

            elif wu == "months":
                start_date = _set_month(self.start, j + 1)
                end_date = _set_month(self.end, j + 1)
                name = month_name[start_date.month]
            else:
                start_date = self.start + timedelta(**{wu[:-1]: j})
                end_date = self.start + timedelta(**{wu[:-1]: j + 1})
                name = None

            items.append(CalendarPeriod(start_date, end_date, name=name))

        # If we ask for items that are beyond 'end' that is an IndexError.
        if any([item.start > self.end for item in items]):
            raise IndexError

        # Iteration asking for a single item should not get a list.
        if stop == start + step:
            return items[0]
        return items

    def len_by_days(self):
        return self.duration / timedelta(days=1) + 1

    def __str__(self):
        return f"({self.start}, {self.end})"

    def subunit_generator(self, unit):
        for sub in self:
            if sub.whole_unit() == unit:
                yield sub
            else:
                yield from sub.subunit_generator(unit)


def _inc_months(dt, i):
    year = dt.year
    month = dt.month
    day = dt.day
    month = month + i
    year += month % 12

    if dt.day == monthrange(dt.year, dt.month)[1]:
        day = monthrange(year, month)[1]

    d = datelike_to_dict(dt)
    d.update({"year": year, "month": month, "day": day})
    return dt.__class__(**d)


class Year(CalendarPeriod):
    season_events = season_events

    def __init__(self, year):
        super().__init__(start=datetime(year, 1, 1),
                         end=datetime(year, 12, 31))
        self.year = year
        self.cal = NotreDame()
        self.THETA_PER_DAY = 360 / self.len_by_days()

    def date_to_day(self, obj):
        return list(self).index(CalendarElement(year=obj.year,
                                                month=obj.month,
                                                day=obj.day))

    def day_to_date(self, i):
        ce = self[i]
        return date(year=ce.year.value, month=ce.month.value, day=ce.day.value)

    def day_to_datetime(self, i):
        return self[i].datetime()

    def to_theta(self, value):
        try:
            dt = value - self.start
        except TypeError:
            try:
                dt = datetime.combine(value, time(0, 0)) - self.start
            except TypeError:
                dt = value

        return dt / timedelta(days=1) * self.THETA_PER_DAY

    def is_weekend(self, datelike):
        return is_weekend(datelike)

    def weekday(self, datelike):
        return weekday(datelike)

    def get_calendar_holidays(self):
        return self.cal.get_calendar_holidays(self.year)

    weekends = weekends


TD_UNITS = ["days", "hours", "minutes", "seconds", "microseconds"]
TD_STORE_UNITS = ["microseconds", "seconds", "days"]


def td_is_zero(td):
    for u in TD_STORE_UNITS:
        if getattr(td, u) != 0:
            return False
    return True
