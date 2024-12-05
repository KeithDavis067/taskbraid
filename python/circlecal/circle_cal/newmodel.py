import calendar
from datetime import datetime, timedelta, date, time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from calendar import monthrange, month_name, day_name
from workalendar.usa import UnitedStates, Indiana
from pytz import timezone
from copy import copy


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

    @classmethod
    def from_attributes(cls, o, set_trailing_zeros=False):
        """ Return a DTPrecision instance from the unit attributes of an object.

        Read the values on the attributes listed in DTPrecision.UNITS and
        return a DTPrecision object with units set to those values. Any unit
        values that return zero will be set to None
        if they are not followed by a smaller unit with a non-zero value.
        Set 'set_trailing_zeros' to True
        to force all zeros to zero.

        In the common case of date and datetime objects these rules imply
        the following behavior:

        datetime.date objects always have a non-zero value for
        year, month, and date, so DTPrecision made from
        datetime.date objects will always have a precision of "day".
        datetime.datetime objects will create a DTPrecision object
        with precision equal to the smallest unit with a nonzero
        value, unless "set_trailing_zeros" is True. In which case they will
        have a precision of "microsecond."

        """
        d = {}
        for u in cls.UNITS:
            try:
                d[u] = getattr(o, u)
            except AttributeError:
                pass
        if d == {}:
            raise TypeError(f"unable to coerce {o} to timelike.")
        if not set_trailing_zeros:
            for u in reversed(cls.UNITS):
                try:
                    if d[u] == 0:
                        d[u] = None
                except KeyError:
                    d[u] = None

        return cls(**d)

    from_datelike = from_attributes
    from_date = from_attributes

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
            # Catch old values to reset if failure.
            old = self.to_dict()
            try:
                # If this is None, all lower values
                # should be cleared to None.
                if value is None:
                    for u in [name] + _subunits(name):
                        super().__setattr__(u, None)
                    return

                # Ensure all superunits are set to
                # a value or set them to their start value.
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
                # should return a range for the month.
                if value in self.ranges[name]:
                    super().__setattr__(name, value)
                else:
                    raise ValueError(f"{value} not in range for {name}")
                # Ensure new value doesn't make lower values out of range.

                for u in _subunits(name):
                    v = getattr(self, u)
                    if v is not None:
                        if v not in self.ranges[u]:
                            raise ValueError(f"Setting {name} would put {u} "
                                             f"out of range.")

            except ValueError as e:
                for u, v in old.items():
                    super().__setattr__(u, v)
                raise e
        # Use normal if this isn't a unit.
        super().__setattr__(name, value)

    def __init__(self, *args, **kwargs):
        params = dict(zip(UNITS, args))
        for i, u in enumerate(params):
            if u in kwargs:
                raise (f"argument for function given by name "
                       f"({u}) and position ({i})")

        params.update(kwargs)

        for u in self.UNITS:
            try:
                setattr(self, u, params[u])
            except KeyError:
                pass

    def to_dict(self, skipnone=False):
        if skipnone:
            return dict([(u, getattr(self, u)) for
                         u in self.UNITS if getattr(self, u) is not None])
        else:
            return dict([(u, getattr(self, u)) for u in self.UNITS])

    def precision(self):
        for u in reversed(self.UNITS):
            if getattr(self, u) is not None:
                return TUnit(u)

    def to_precision(self, prec):
        p = self.precision()
        if p <= prec:
            return copy(self)

        new = copy(self)

        try:
            u = prec.name
        except AttributeError:
            u = prec
        try:
            setattr(new, u, 0)
        except ValueError:
            setattr(new, u, 1)
        return new

    def to_datetime(self, force=False):
        """ Convert to a datetime.

        keywords:
            force: If true, set year, time, and day to smallest value
            in range before converting to datetime. Avoids error.

        If precision is less than 1 day, let datetime
        this will raise an error.
        """
        dt_required = ["year", "month", "day"]
        if force:
            cp = self.__class__(**self.to_dict())
            for u in dt_required:
                if getattr(cp, u) is None:
                    setattr(cp, u, cp.ranges[u].start)
        else:
            cp = self
        return datetime(**cp.to_dict(skipnone=True))

    def __eq__(self, o):
        """ Determine equlity of value and precision. See details.

        DTPrecision objects are equal to objects that meet
        the following conditions:

        1) When converted to a DTPrecision object their precision
        is not greater than self.
        3) If an attribute is None on self, then it must be
        None, undefined, or zero on other.
        4) If the attribute is not None on self, then it must
        be equal to the value on other.
        """
        if self is o:
            return True

        # If self is more precise then false.
        if self.precision() > self.__class__.from_attributes(o).precision():
            return False

        for u in self.UNITS:

            try:
                if getattr(self, u) != getattr(o, u):
                    if getattr(self, u) is None:
                        # Declare nonequal if self is None and
                        # other value is not zero.
                        if getattr(o, u) != 0:
                            return False
                    # self and other unit values don't match and
                    # self isn't None, then nonequal.
                    else:
                        return False

            # Of other unit is not an attribute.
            except AttributeError:
                # If object doesn't at least have a "year" attribute
                # then it isn't a datelike.
                if u == "year":
                    raise TypeError(f"cannot compare non-datelike to "
                                    f"{self.__class__.__name__}.")
                # If the attribute isn't declared, and self is not None
                # then nonequal.
                if getattr(self, u) is not None:
                    return False
        return True

    def __gt__(self, o):
        return self.to_datetime(force=True) > _any_to_datetime(o)

    def __lt__(self, o):
        return self.to_datetime(force=True) < _any_to_datetime(o)

    def __sub__(self, o):
        return self.to_datetime(force=True) - _any_to_datetime(o)

    def __rsub__(self, o):
        return _any_to_datetime(o) - self.to_datetime(force=True)

    def __add__(self, o):
        p = self.precision()
        new = self.from_attributes(self.to_datetime(force=True) + o)
        if p < new.precision():
            for u in self.UNITS:
                if u >= new.precision():
                    setattr(new, u, new.ranges.start)

        return new

    def __radd__(self, o):
        return o + self.to_datetime(force=True)

    def __repr__(self):
        d = self.to_dict(skipnone=True)
        colons = []
        dashes = [str(d["year"])]

        for u in ["month", "day"]:
            try:
                if d[u] is not None:
                    dashes.append(f"{d[u]:02}")
            except KeyError:
                pass

        for u in ["hour", "minute", "second"]:
            try:
                if d[u] is not None:
                    colons.append(f"{d[u]:02}")
            except KeyError:
                pass
        try:
            if d["microsecond"] is not None:
                mic = f"{d["microsecond"]:06}"
            else:
                mic = ""
        except KeyError:
            mic = ""

        dashes = "-".join(dashes)
        colons = ":".join(colons)
        s = " ".join([dashes, colons])
        if mic != "":
            s += "." + mic
        return self.__class__.__name__ + ":" + s

    def increment(self):
        u = self.precision().name
        nxt = getattr(self, u) + 1
        while nxt not in self.ranges[u]:
            setattr(self, u, self.ranges[u].start)
            u = _superunit(u)
            if u is None:
                raise StopIteration
            nxt = getattr(self, u) + 1
        setattr(self, u, nxt)

    def __next__(self):
        self.increment()
        return copy(self)

    def __iter__(self):
        return self.__class__.from_attributes(self)


def _any_to_datetime(o):
    if isinstance(o, datetime):
        return o
    try:
        return o.to_datetime(force=True)
    except AttributeError:
        pass
    try:
        return datetime.combine(o, time())
    except TypeError as e:
        raise TypeError("unable to coeerce object to datetime.") from e


class Test_DTPrecision:
    def test_to_dict(self):
        dtp = DTPrecision()
        assert dtp.to_dict() == dict([(u, None) for u in UNITS])
        assert dtp.to_dict(skipnone=True) == {}
        dtp = DTPrecision(year=2024, day=1)
        assert dtp.to_dict() == dict(year=2024,
                                     month=1,
                                     day=1,
                                     hour=None,
                                     minute=None,
                                     second=None,
                                     microsecond=None)
        assert dtp.to_dict(skipnone=True) == dict(year=2024,
                                                  month=1,
                                                  day=1)

    def test_init(self):
        dtp = DTPrecision(year=2024)
        assert dtp.year == 2024
        assert dtp.minute is None
        dtp = DTPrecision(year=2024, day=1, minute=20)
        assert dtp.year == 2024
        assert dtp.day == 1
        assert dtp.minute == 20

        dtp = DTPrecision(2024, day=1)
        assert dtp.year == 2024
        assert dtp.month == 1
        assert dtp.day == 1
        for u in dtp.UNITS[3:]:
            assert getattr(dtp, u) is None

        dtp = DTPrecision(2024, 1, 1, 0)

        assert dtp.year == 2024
        assert dtp.day == 1
        assert dtp.month == 1
        assert dtp.hour == 0

        for u in dtp.UNITS[4:]:
            assert getattr(dtp, u) is None

        with pytest.raises(TypeError):
            dtp = DTPrecision(2024, 1, 1, day=1)

    def test_assign(self):
        dtp = DTPrecision()
        # Default is None for everything.
        for u in dtp.UNITS:
            assert getattr(dtp, u) is None

        # Setting the smallest unit should set all
        # previous units to their smallest value.
        dtp.microsecond = 0
        # Make sure when month and year was set,
        # day ranges was set.
        assert dtp.ranges["day"] == range(1, 32)
        # Make sure every unit is set to it's start value.
        for u, r in dtp.ranges.items():
            assert getattr(dtp, u) == r.start

        # Ensure error is raised when outside value.
        dtp.year = 2024
        dtp.month = 2
        assert dtp.ranges["day"] == range(1, 30)
        with pytest.raises(ValueError):
            dtp.day = 30

        with pytest.raises(ValueError):
            dtp = DTPrecision(year=2000, microsecond=10000000)

        # Ensure changing month to February throws error when
        # day is out of range.
        #
        dtp = DTPrecision(year=2002, month=1, day=31)
        with pytest.raises(ValueError):
            dtp.month = 2

    def test_clear(self):
        dtp = DTPrecision(year=2024, month=4, day=1, minute=10)
        assert dtp.to_dict() == dict(year=2024,
                                     month=4,
                                     day=1,
                                     hour=0,
                                     minute=10,
                                     second=None,
                                     microsecond=None)
        dtp.month = None
        assert dtp.to_dict() == dict(year=2024,
                                     month=None,
                                     day=None,
                                     hour=None,
                                     minute=None,
                                     second=None,
                                     microsecond=None)

    def test_precision(self):
        dtp = DTPrecision(year=2024, month=1, day=10)
        assert dtp.precision() == "day"
        dtp.microsecond = 0
        assert dtp.precision() == "microsecond"

    def test_to_datetime(self):
        dtp = DTPrecision(year=2023, month=1, day=1)
        assert datetime(2023, 1, 1) == dtp.to_datetime()
        dtp = DTPrecision(year=2023, month=1)
        with pytest.raises(TypeError):
            dtp.to_datetime()

    def test_eq(self):
        dtp = DTPrecision()
        odtp = dtp
        assert odtp == dtp

        odtp == DTPrecision()

        assert odtp == dtp

        assert not (DTPrecision(2023) == DTPrecision(2024))
        assert (DTPrecision(2023) != DTPrecision(2024))

        assert DTPrecision(2023, 1, 1) == date(2023, 1, 1)
        assert (DTPrecision(2023, 1, 1) == datetime(2023, 1, 1))
        assert not (DTPrecision(2023, 1, 1) == datetime(2023, 1, 1, 1))
        assert DTPrecision(year=2023,
                           month=1,
                           day=1,
                           hour=0,
                           minute=0,
                           second=0,
                           microsecond=0) == datetime(2023, 1, 1, 0, 0, 0, 0)

        def test_to_precision(self):
            dtp = DTPrecision(2024, minute=10)
            assert dtp.year == 2024
            assert dtp.month == 1
            assert dtp.day == 1
            assert dtp.minute == 10
            assert dtp.second is None
            assert dtp.microsecond is None

            out = dtp.to_precision("second")
            assert dtp.year == 2024
            assert dtp.month == 1
            assert dtp.day == 1
            assert dtp.minute == 10
            assert dtp.second is 0
            assert dtp.microsecond is None

            assert out is dtp


class TUnit:
    UNITS = UNITS

    @ property
    def subunit(self):
        return _subunit(self)

    @ property
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

    def __repr__(self):
        return "Unit: " + self.name


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

    @ property
    def start(self):
        # Holding start as unmodifiable after creation for now.
        # May edit when modifying stop and end automatically
        # is implemented.
        return self._start

    @ property
    def stop(self):
        """ The first moment of the next time period.
        Stop is the first moment that is definitely in another time period.
        Analogous to 'stop' in range objects, the item can iterate to this moment
        but should not return it.
        """
        return self._stop

    @ property
    def end(self):
        """ The last microsecond of this period.
        """
        return self.stop - timedelta(microseconds=1)

    @property
    def unit(self):
        return min(self.start.precision(), self.stop.precision())

    @property
    def subunit(self):
        return _subunit(self.unit)

    @property
    def duration(self):
        return self.stop - self.start

    def __init__(self, start, stop=None,
                 duration=None, name=None, all_zeros_significant=False):
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
        self._start = DTPrecision.from_attributes(
            start, set_trailing_zeros=all_zeros_significant)
        if stop is not None:
            stop = DTPrecision.from_attributes(
                stop,  set_trailing_zeros=all_zeros_significant)

        elif duration is not None:
            stop = self.start + duration

        # If we haven't found a stop yet, set it to the next value of precision.
        if stop is None:
            stop = next(iter(self.start))

        self._stop = stop

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
        #
    def __getitem__(self, i):
        l = len(self)
        try:
            start = i.start
        except AttributeError:
            start = i

        if start > l - 1:
            raise IndexError

        try:
            if i.stop is None:
                stop = start + 1
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

        if stop > len(self):
            raise IndexError

        items = []
        counter = iter(self.start)
        # Increment to start
        for i in range(0, start):
            counter.increment()
        for i in range(start, stop, step):
            low = copy(counter)
            items.append(self.__class__(low, next(counter)))
            # Roll forward steplength.
            for j in range(step - 1):
                counter.increment()

        if len(items) == 1:
            return items[0]
        return items

    def __len__(self):
        match self.unit:
            case "year":
                return self.stop.year - self.start.year
            case "month":
                return self.stop.month - self.start.month
            case _:
                return (self.stop - self.start) / timedelta(**{self.unit + "s": 1})

    def __repr__(self):
        return f"[{self.start}, {self.stop}]"


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
