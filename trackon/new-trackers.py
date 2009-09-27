from cgi import FieldStorage
from logging import debug, error, info
from google.appengine.api.labs import taskqueue as tq
from trackon import tracker

new_queue = tq.Queue('new-trackers')

def main():
    args = FieldStorage()
    if 'tracker-address' in args and args['tracker-address'].value:
        addr = args['tracker-address'].value 
        (r, url) = tracker.check(addr)
        debug("Fetching %s"%url)
        if 'error' not in r:
            debug("Added tracker: %s"%addr)
            tracker.add(addr, r)
        else:
            info("Initial tracker check for %s failed: %s" % (url, r['error']))
            attp = int(args['attempts'].value)+1
            if attp > 4: # TODO: We should raise the number of attempts?
                info("Giving up after %d attempts to contact: %s" % (attp, addr))
                return 
            info("Attempt %d scheduled in %d seconds." % (attp, attp*20))
            params = {'tracker-address': addr, 'attempts': attp }
            task = tq.Task(params=params, countdown=attp*30)
            new_queue.add(task)


if __name__ == '__main__':
    main()
