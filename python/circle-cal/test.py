from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from gcsa.recurrence import Recurrence, DAILY, SU, SA

from beautiful_date import Jan, Apr


calendar = GoogleCalendar('keithwdavis@gmail.com',
                          credentials_path='/Users/kdavis10/.credentials/client_secret_3681359253-cj6ds937cv5p30vn8tbms112bjplms95.apps.googleusercontent.com.json')
event = Event(
    'Breakfast',
    start=(1 / Jan / 2023)[9:00],
    recurrence=[
        Recurrence.rule(freq=DAILY),
        Recurrence.exclude_rule(by_week_day=[SU, SA]),
        Recurrence.exclude_times([
            (19 / Apr / 2019)[9:00],
            (22 / Apr / 2019)[9:00]
        ])
    ],
    minutes_before_email_reminder=50
)

calendar.add_event(event)

for event in calendar:
    print(event)
