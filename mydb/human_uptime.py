import datetime
import dateutil
from dateutil import parser
import pytz


def human_uptime(started):
    global day_str
    a = dateutil.parser.parse(started)
    b = datetime.datetime.now(pytz.timezone('US/Pacific'))
    delta = b - a
    if delta.days > 0:
        weeks = delta.days / 7
        days = delta.days % 7
        if days == 1:
            day_str = 'day'
        elif days > 1:
            day_str = 'days'
        if weeks == 1:
            msg = "1 week"
        elif weeks > 1:
            msg = "%d weeks" % weeks
        else:
            msg = ''
        if days > 0:
            if weeks > 0:
                msg += ' and '
            msg += "%d %s ago" % (days, day_str)
        else:
            msg += ' ago'
    elif delta.seconds > 1:
        if delta.seconds > 3600:
            hours = delta.seconds / 3600
            minutes = (delta.seconds - (hours * 3600)) / 60
            if hours > 2:
                msg = "more than %s hours ago" % hours
            else:
                if minutes > 0:
                    msg = "%s hours %s minutes ago" % (hours, minutes)
                else:
                    msg = "%s hours ago" % (hours, minutes)
        elif delta.seconds > 60:
            minutes = delta.seconds / 60
            seconds = delta.seconds % 60
            if seconds != 0:
                msg = "%d minutes %d seconds ago" % (minutes, seconds)
            else:
                msg = "%d minutes ago" % (minutes)
        else:
            msg = "%d seconds ago" % delta.seconds
    else:
        msg = "about a second ago"
    return msg
