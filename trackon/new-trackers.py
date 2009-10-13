from cgi import FieldStorage
from logging import debug, error, info
from google.appengine.api.labs import taskqueue as tq
from trackon import tracker
from trackon.gaeutils import logmsg

incoming_queue = tq.Queue('new-trackers')

def main():
    args = FieldStorage()
    if 'tracker-address' in args and args['tracker-address'].value:
        addr = args['tracker-address'].value 
        (r, url) = tracker.check(addr)
        debug("Fetching %s"%url)
        if 'error' not in r:
            tracker.add(addr, r)
            logmsg("Check of %s was successful, added to proper tracker list!" % addr, 'incoming')
        else:
            logmsg("Incoming tracker check for %s failed: %s" % (addr, r['error']), 'incoming')
            attp = int(args['attempts'].value)+1
            if attp > 2: # TODO: We should raise the number of attempts?
                logmsg("Giving up after %d attempts to contact: %s" % (attp, addr), 'incoming')
                return 

            params = {'tracker-address': addr, 'attempts': attp }
            task = tq.Task(params=params, countdown=attp*50)
            incoming_queue.add(task)


if __name__ == '__main__':
    main()
