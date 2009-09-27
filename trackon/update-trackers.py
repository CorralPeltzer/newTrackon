from cgi import FieldStorage
from logging import debug, error, info
from time import time
from trackon import tracker

MAX_MIN_INTERAVAL = 60*60*5
DEFAULT_CHECK_INTERVAL = 60*10


def main():
    args = FieldStorage()
    now = int(time())

    if 'tracker-address' in args:
        t = args['tracker-address'].value
        (r, url) = tracker.check(t)

        nxt = DEFAULT_CHECK_INTERVAL
        if 'response' in r and 'min interval' in r['response']:
            nxt = r['response']['min interval']

            if nxt > MAX_MIN_INTERVAL:
                nxt = MAX_MIN_INTERVAL
                
        r['next-check'] = now+nxt
        tracker.update(t, r)
        if 'error' in r:
            info("Update failed for %s: %s" % (t, r['error']))
        
    else:
        ti = tracker.allinfo() or {}
        for t in ti:
            if 'next-check' not in ti[t] or ti[t]['next-check'] < now: 
                tracker.schedule_update(t)


if __name__ == '__main__':
    main()
