import calendar
from datetime import datetime, timedelta
from calendar import monthrange, month_name, day_name
try:
    import pandas as pd
except ImportError:
    pass

# TODO: Add event class. Recase Year_Data as and "event" class and add make
# Year_Data a subclass.


class Event:


class Year_Data:

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, year):
        try:
            if self.date.year != year:
                self._year = year
            del self.date
        except (AttributeError, TypeError):
            pass

        self._year = year

    @property
    def date(self):
        if self._date is None:
            return datetime.date(self.year, 1, 1)
        return self._date

    @date.setter
    def date(self, date):
        if date.year != self.year:
            raise ValueError(f"Date: {date} is outside instance year.")
        self._date = date

    @date.deleter
    def date(self):
        self._date = None

    def __init__(self, year=None, date=None):
        if year is None:
            year = datetime.now().year
        self.year = year

        if date is None:
            date = datetime(self.year, 1, 1)
        self.date = date

    def start(self):
        return datetime(self.year, 1, 1)

    def end(self):
        """ Return a dateime for just before midnight on the last day."""
        return datetime(self.year+1, 1, 1) - timedelta(microseconds=1)

    def length(self):
        """ Return the length of the calendar year in days."""
        return datetime(self.year+1, 1, 1) - self.start()

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
            end = datetime(self.year + 1, 1, 1)

        day = timedelta(1)
        # If start is an int, create a date from it.
        try:
            start = self.number_as_date(start)
        except TypeError:
            # If not an int, it may be datetime.
            pass
        try:
            if not (self.start() <= start < end):
                raise ValueError(f"start must be in {self._year}")
        except TypeError as e:
            if not (self.start().date() <= start.date() < end.date()):
                raise TypeError(
                    "start must be a number, datetime.datime, "
                    "or datetime.date instance.") from e
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
