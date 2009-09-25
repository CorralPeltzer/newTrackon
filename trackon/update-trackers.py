from logging import debug, error, info
from cgi import parse_qs, FieldStorage
from time import time
from google.appengine.api.labs import taskqueue as tq
from google.appengine.api import memcache as mc
from trackon import tracker

update_queue = tq.Queue('update-trackers')

def main():
    args = FieldStorage()

    if 'tracker-address' in args:
        t = args['tracker-address'].value
        (r, url) = tracker.check(t)
        tracker.update(t, r)
        if 'error' in r:
            info("Update failed for %s: %s" % (t, r['error']))
        
    else:
        for t in (mc.get('tracker-list') or []):
            params = {'tracker-address': t}
            task = tq.Task(params=params) # TODO set countdown to min interval
            update_queue.add(task)
        

if __name__ == '__main__':
    main()
