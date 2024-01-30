from datetime import datetime, date, timedelta

__all__ = ['date_to_theta', 'events_to_dur',
           'events_to_mid', 'events_to_polar']


def date_to_theta(d, year=None):
    if year is None:
        year = Year_Data(datetime.now().year)
    try:
        day_to_theta = 360 / len(year)
    except TypeError:
        year = Year_Data(datetime.now().year)
        day_to_theta = 360 / len(year)
    day = year.int_from_date(d)

    return day * day_to_theta


def events_to_dur(events):
    try:
        dur = events[:, 1] - events[:, 0]
    except IndexError:
        dur = events[1:] - events[0:-1]
    except TypeError:
        try:
            dur = [start - end for start, end in events]
        except TypeError:
            dur = [start - end for start, end in zip(events[1:], events[:-1])]
    return dur


def events_to_mid(events, dur=None):
    if dur is None:
        dur = events_to_dur(events)

    try:
        mid = events[:, 0] + dur/2
    except IndexError:
        mid = (events[1:] - events[:-1]) + dur/2
    except TypeError:
        try:
            mid = [start + dur/2 for start,
                   dur in zip([ev[0] for ev in events], dur)]
        except TypeError:
            mid = [start + dur/2 for start,
                   dur in zip([ev for ev in events], dur)]
    return mid


def events_to_polar(events, days_to_theta=360/365.25, zero_date=date(datetime.today().year, 1, 1)):
    try:
        import numpy as np
    except ImportError:
        pass

    dur = events_to_dur(events)
    mid = events_to_mid(events, dur)

    # Array of numbers or single value.
    try:
        theta = dur * days_to_theta
    except TypeError:
        # Array of dates.
        try:
            theta = (np.vectorize(datetime.toordinal)(mid) -
                     zero_date.toordinal()) * days_to_theta
        except (TypeError, NameError, UnboundLocalError):
            # If no numpy.
            try:
                theta = [(m.toordinal() - zero_date.toordinal())
                         * days_to_theta for m in mid]
            # If neigther a date nor a array.
            except TypeError:
                theta = [m * days_to_theta for m in mid]

    try:
        width = dur * days_to_theta
    except TypeError:
        # Array of dates.
        try:
            width = np.vectorize(timedelta.days)(dur) * days_to_theta
        except (TypeError, NameError, UnboundLocalError):
            # If no numpy.
            try:
                width = [d.days * days_to_theta for d in dur]
            # If neigther a date nor a array.
            except TypeError:
                width = [d * days_to_theta for d in dur]

    return theta, width
