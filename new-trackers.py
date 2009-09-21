from logging import debug, error, info
from cgi import parse_qs, FieldStorage
from google.appengine.api.labs import taskqueue as tq
from google.appengine.api import memcache as mc
import tracker

new_trackers_queue = tq.Queue('new-trackers')

def main():
    args = FieldStorage()
    if 'tracker-address' in args and args['tracker-address'].value:
        addr = args['tracker-address'].value 
        (success, d, url) = tracker.check(addr)
        debug("Fetching %s"%url)
        if success:
            debug("Added tracker: %s"%addr)
            tracker.add(addr, d)
        else:
            info("Initial tracker check for %s failed: %s" % (url, d))
            attp = int(args['attempts'].value)+1
            info("Attempt %d scheduled in %d seconds."%(attp, attp*20))
            if attp > 30:
                return # We give up XXX log this somewhere
            params = {'tracker-address': addr, 'attempts': attp }
            task = tq.Task(params=params, countdown=attp*30)
            new_trackers_queue.add(task)


if __name__ == '__main__':
    main()
