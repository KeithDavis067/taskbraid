from datetime import datetime, time, date, timedelta
from .model import CalendarElement, TimeDigit, TimeRegister, Year, EventWrap, ETZ as TZ
import plotly.graph_objects as go
import calendar
import numpy as np
import pandas as pd

# Fundamental ploting plan:
# Central .2 is taken up by the year value.
# from there events are sorted by:
#      1 month < dur
#      1 week  < dur < 1 month
#      1 day   < dur < 1 week
#      1 hour  < dur < 1 day
#              < dur < 1 hour

POLAR_CORE = .2  # The amount teken up by the central text.
NGROUPS = 5
RSPACING = 0
DR = (1 - POLAR_CORE - RSPACING * (NGROUPS - 1)) / NGROUPS


def localize_any(obj, tz):
    try:
        return tz.localize(obj)
    except ValueError:
        if obj.tzinfo:
            return obj
    except AttributeError:
        return tz.localize(datetime.combine(obj, time(0, 0)))
    return obj


def to_theta(datevalue, year=None):
    try:
        year = Year(year)
    except TypeError:
        pass

    return year.to_theta(datevalue)


def events_to_dataframe(events):
    """ Extract calendar specific details from events into a dataframe."""
    df = pd.DataFrame(data=events, columns=["Event_obj"])

    try:
        df["duration"] = df["Event_obj"].apply(lambda ev: ev.duration)
    except AttributeError:
        df["Event_obj"] = df["Event_obj"].apply(lambda eve: EventWrap(eve))
        df["duration"] = df["Event_obj"].apply(lambda ev: ev.duration)

    df["mid"] = pd.to_datetime(df["Event_obj"].apply(
        lambda ev: localize_any(ev.mid, TZ)), utc=True).dt.tz_convert(TZ)
    df["start"] = pd.to_datetime(df["Event_obj"].apply(
        lambda ev: localize_any(ev.start, TZ)), utc=True).dt.tz_convert(TZ)
    df["end"] = pd.to_datetime(df["Event_obj"].apply(
        lambda ev: localize_any(ev.end, TZ)), utc=True).dt.tz_convert(TZ)

    df["summary"] = df["Event_obj"].apply(lambda ev: ev.summary)
    return df


def selected_cals_to_dataframe(gcal, selcal, year):
    """Return a dataframe for plotly from a collection of calendars."""
    try:
        year = Year(year.year)
    except AttributeError:
        year = Year(year)

    dfs = []
    for cal in selcal:
        events = gcal.get_events(year.start,
                                 year.end,
                                 single_events=True,
                                 calendar_id=cal.calendar_id,
                                 )
        df = events_to_dataframe(events)
        dfs.append(df)
        df["color"] = cal.background_color
        df["calendar_id"] = cal.calendar_id
        df["calendar"] = cal.summary
        df["weekday"] = df.start.apply(year.weekday)

    df = pd.concat(dfs, axis="rows", ignore_index=True)
    return df


def polar_to_cart(r, theta):
    x = r * np.sin(theta)
    y = r * np.cos(theta)
    return (x, y)
