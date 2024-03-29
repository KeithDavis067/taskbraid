import calendar
from datetime import datetime, timedelta
from calendar import monthrange, month_name, day_name
try:
    import pandas as pd
except ImportError:
    pass


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
            raise ValueError(
                f"Cannot set a date with year outside of instance year.")
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

    def first_day(self):
        return datetime(self.year, 1, 1)

    def last_day(self):
        return datetime(self.year, 12, 31)

    def length(self):
        return self.last_day() - self.first_day() + timedelta(1)

    def weekday(self, n=None):
        if n is None:
            return self.date.weekday()
        else:
            return self.weekday_from_int(n)

    def get_year(self):
        return self.year()

    def date_from_int(self, n):
        return self.first_day() + timedelta(n)

    def int_from_date(self, d=None):
        if d is None:
            d = self.date

        try:
            return (d - self.first_day().date()).days
        except TypeError:
            return (d.date() - self.first_day().date()).days

    def weekday_from_int(self, n):
        return self.date_from_int(n).weekday()

    def monthrange(self, month=None):
        if month is None:
            month = self.date.month
        return monthrange(self.year, month)

    def iterdates(self, start=0, end=None):

        if end is None:
            end = self.last_day()

        day = timedelta(1)
        # If start is an int, create a date from it.
        try:
            start = self.date_from_int(start)
        except TypeError as e:
            # If not an int, it may be datetime.
            pass
        try:
            if not (self.first_day() <= start <= self.last_day()):
                raise ValueError(f"start must be in {self._year}")
        except TypeError as e:
            raise TypeError("start must be an integer or datetime.") from e
        while self.first_day() <= start <= self.last_day():
            yield start
            start += day

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
