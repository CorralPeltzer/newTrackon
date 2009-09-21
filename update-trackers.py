from logging import debug, error, info
from cgi import parse_qs, FieldStorage
from time import time
from google.appengine.api.labs import taskqueue as tq
from google.appengine.api import memcache as mc
import tracker

update_queue = tq.Queue('update-trackers')

def main():
    args = FieldStorage()

    if 'tracker-address' in args:
        t = args['tracker-address'].value
        (success, data, url) = tracker.check(t)
        mc.set(t, data, namespace="status")
        tim = int(time())
        mc.set("%s!%d" % (t, tim), data, namespace="logs")
        l = mc.get(t, namespace="logs") or []
        l.insert(0, tim)
        mc.set(t, l[:64]) # Keep 64 samples
        
    else:
        for t in (mc.get('tracker-list') or []):
            params = {'tracker-address': t}
            task = tq.Task(params=params) # TODO set countdown to min interval
            update_queue.add(task)
        

if __name__ == '__main__':
    main()
