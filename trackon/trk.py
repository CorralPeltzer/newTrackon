from trackon import tracker, web, gaeutils
from urlparse import urlparse 
from os import environ
from google.appengine.api import memcache as MC

def main():
    tn = environ['PATH_INFO'].split('/')[2].split('?')[0]
    if not tn:
        print "Provide a proper tracker name!"
        return

    t = tracker.gettrk(tn)
    if not t:
        print "Tracker name '%s' not found."%tn
        return

    web.renderpage('trk', trka=t[0], trk=t[1], logs=tracker.getlogs(t[0]))


if __name__ == '__main__':
    main()
