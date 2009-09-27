from cgi import FieldStorage
from logging import debug, error, info
from time import time
from google.appengine.api.labs import taskqueue as tq
from trackon import tracker

update_queue = tq.Queue('update-trackers')
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
                params = {'tracker-address': t}
                task = tq.Task(params=params)
                update_queue.add(task)
        

if __name__ == '__main__':
    main()
