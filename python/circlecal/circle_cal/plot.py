from datetime import datetime, time, date, timedelta
from .model import CalendarElement, TimeDigit, TimeRegister
import plotly.graph_objects as go
import calendar

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
print(DR)


def to_theta(datevalue, year=None):
    if year is None:
        try:
            year = datevalue.year
        except AttributeError:
            year = datetime.today().year

    ce = CalendarElement(year=year)
    days = ce.date_to_unit(datevalue)
    return 360 / len(list(ce.recursive_iteration("day"))) * days


def event_to_barpolar_values(event, days_to_theta=None):
    if days_to_theta is None:
        days_to_theta = 365 / 360

    if timedelta(days=7) < event.duration:
        group = 0

    if timedelta(days=1) < event.duration <= timedelta(days=7):
        group = 1

    if timedelta(days=1) == event.duration:
        group = 2

    if timedelta(hours=1) <= event.duration < timedelta(days=1):
        group = 3
    if event.duration < timedelta(hours=1):
        group = 4

    base = POLAR_CORE + group * (DR + RSPACING)
    r = DR

    width = event.duration / timedelta(days=1) * days_to_theta
    theta = to_theta(event.mid)
    return (base, r, theta, width)


def events_to_trace(events, days_to_theta=None):
    b = []
    r = []
    t = []
    w = []
    tx = []
    for i, event in enumerate(events):
        bb, rr, tt, ww = event_to_barpolar_values(event, days_to_theta)
        b.append(bb)
        r.append(rr)
        t.append(tt)
        w.append(ww)
        tx.append(" ".join((str(i), str(event.mid),
                  event.summary)))
    return go.Barpolar(base=b, r=r, theta=t, width=w, text=tx)
