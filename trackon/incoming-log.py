from trackon import tracker, web, gaeutils
from google.appengine.api import memcache as MC

def main():
    l = gaeutils.getmsglog('incoming') 
    web.renderpage('incoming-log', msgs=l)


if __name__ == '__main__':
    main()
