from logging import debug, error, info
from hashlib import md5
from time import time
from urlparse import urlparse 
from urllib import unquote as url_unquote
from google.appengine.api.urlfetch import fetch, Error as FetchError, DownloadError
from google.appengine.api import memcache as MC
from google.appengine.api import datastore as DS
from google.appengine.api.labs import taskqueue as TQ
from trackon.bencode import bdecode
from trackon.gaeutils import logmsg, getentity

"""
Memcache namespaces:
    'status': tracker-url -> Dict with latest tracker info
    'logs': "%s!%d" % (tracker-url, time) -> Historical tracker info.
    'logs': tracker-url -> List of latest timestamps to reach historical info.

Keys in default namespace:
    'tracker-list' -> List of urls of currently live trackers.

Silly requirements made by various obnoxious trackers:
    - Require 'compact=1', instead of just returning compact format by default.
    - Require 'key'.
    - Require 'uploaded', 'downloaded' and 'left'. (http://tracko.appspot.com/announce)
"""


update_queue = TQ.Queue('update-trackers')
incoming_queue = TQ.Queue('new-trackers')

def trackerhash(addr):
    """Generate a 'fake' info_hash to be used with this tracker."""
    return md5(addr).hexdigest()[:20]

def genqstr(h):
    pid = "-TO0001-XX"+str(int(time())) # 'random' peer id
    return "?info_hash=%s&port=999&peer_id=%s&compact=1&uploaded=0&downloaded=0&left=0" % (h, pid)

def check_ssl(addr):
    return check(addr.replace('http://', 'https://'))

def check(addr):
    """Check if a tracker is up."""
    thash = trackerhash(addr) # The info_hash we will use for this tracker 
    d = {}
    d['query-string'] = genqstr(thash) 
    try:
        t1 = time()
        r = fetch(addr+d['query-string'], deadline=10)
        d['latency'] = time() - t1
    except DownloadError, e:
        d['error'] = "Could not reach tracker." # XXX Should find out why!
    except FetchError, e:
        d['error'] = unicode("Fetchurl error: %s" % repr(e), errors='replace')
    
    if 'error' in d:
        d['latency'] = time() - t1
        return d


    if r.status_code != 200:
        d['error'] = "Unexpected HTTP status: %d" % r.status_code
    
    elif not r.content:
        d['error'] = "Got empty HTTP response."

    else:
        try:
            d['response'] = bdecode(r.content)
        except:
            d['error'] = unicode("Couldn't bdecode response: %s." % r.content[:128], errors='replace')

    if 'response' in d:
        if 'failure reason' in d['response']:
            d['error'] = "Tracker failure reason: \"%s\"." % unicode(d['response']['failure reason'], errors='replace')
        elif 'peers' not in d['response']:
            d['error'] = "Invalid response, 'peers' field is missing!"

    # TODO Do a more extensive check of what was returned

    return d


def update(t, info):
    """
    Refresh memcache with new info, log status, calculate uptime, ...; Returns 
    the updated info dict.
    """

    if t.startswith('https://'):
        t = t.replace('https://', 'http://')
        old = MC.get(t, namespace="status") or {}
        # If ssl worked, try it five times before giving it up.
        if 'error' in info:
            if old.get('ssl', 0) > 0:
                info['ssl'] = old['ssl'] - 1
            else:
                info['ssl'] = 0
                info['next-check'] = 0 # Force imediate (non-ssl) re-check
        else:
            info['ssl'] = 5

    r = getentity('Tracker', t) or {}

    if 'title' in r:
        info['title'] = r['title']
    else:
        info['title'] = t.replace('http://', '')

    if 'home' in r:
        info['home'] = r['home']
    # Don't try to guess homepage, it doesn't work most of the time
    #else:
    #    info['home'] = '/'.join(t.replace('//tracker.','//www.').split('/')[:-1])
    if 'name' in r:
        info['name'] = r['name']

    tim = int(time())
    info['updated'] = tim

    # Save status log
    MC.set("%s!%d" % (t, tim), info, namespace='logs')
    l = MC.get(t, namespace='logs') or []
    l.insert(0, tim)
    MC.set(t, l[:64], namespace='logs') # Keep 64 samples

    # Uptime calculation (XXX Wasteful, we fetch the info we just stored!)
    s = MC.get_multi(["%s!%d" % (t, tm) for tm in l], namespace='logs').values()
    e = sum(1 for x in s if ('error' in x))
    i = len(s)
    if i:
        info['uptime'] = (i-e)*100/i
    else:
        info['uptime'] = 0 # Not sure if 0 or 100 makes more sense here...

    # Finally save the new status
    MC.set(t, info, namespace="status")

    return info


def add(t, info):
    info = update(t, info)

    tl = DS.Entity('Tracker', name=t)
    tl['home'] = info['home']
    tl['title'] = info['title']
    DS.Put(tl)

    # Add t to cache list
    lc = MC.get('tracker-list')
    if not lc:
        allinfo() # The tracker list got lost, recover it before we add to it!
        lc = MC.get('tracker-list') or []

    if t not in lc:
        lc.append(t) # XXX Race with remove()
        MC.set('tracker-list', lc)

    debug("Added tracker: %s"%t)

def delete(t):
    e = getentity('Tracker', t)
    DS.Delete(e.key())
    MC.delete(t, namespace='status')

    lc = MC.get('tracker-list') or []
    if t in lc:
        lc.remove(t) # XXX Race with add()
        MC.set('tracker-list', lc)


import re
UCHARS = re.compile('^[a-zA-Z0-9_\-\./:]+$')
# http://code.google.com/p/pubsubhubbub/source/browse/trunk/hub/main.py?r=256#198
# This two are *implicity*, so to avoid duplicate urls we don't allow them: 80, 443.
GAE_ALLOWED_PORTS = frozenset([4443, 8080, 8081, 8082, 8083, 8084, 8085,
                               8086, 8087, 8088, 8089, 8188, 8444, 8990])
def incoming(t):
    """Add a tracker to the list to check before adding to the proper tracker list"""

    # We trat https urls as plain http, will check if https is supported as part of
    # standard tracker testing process.
    u = urlparse(url_unquote(t).replace('https://', 'http://'))
    if u.scheme != 'http':
        return "Unsupported URL scheme."
    
    if UCHARS.match(u.netloc) and  UCHARS.match(u.path):
        if u.port and u.port not in GAE_ALLOWED_PORTS:
            return "Tracker on unsuported port, see FAQ for details."
        else:
            t = "%s://%s%s" % (u.scheme, u.netloc.lower(), u.path)
    else:
        return "Invalid announce URL!"

    # This is not 100% reliable but should keep dupes most of the time.
    if MC.get(t, namespace='status'):
        return "Tracker already being tracked!"

    # XXX Need some kind of rate-limiting to avoid abuse / DoS

    task = TQ.Task(params={'tracker-address': t, 'attempts': 0})
    incoming_queue.add(task)
    logmsg("Added %s to the incoming queue of trackers to check." % t, 'incoming') 


def allinfo():
    tl = MC.get('tracker-list')

    if not tl:
        # Fresh install or tracker-list fell off memcache
        # Try to recover it from datastore
        q = DS.Query('Tracker', keys_only=True)
        tl = [k.name() for k in q.Get(100)]
        MC.set('tracker-list', tl)

    td = MC.get_multi(tl, namespace='status')

    # Look for any trackers that might have fallen from memcache
    for t in tl:
        if t not in td:
            schedule_update(t)

    return td

def schedule_update(t):
    params = {'tracker-address': t}
    task = TQ.Task(params=params)
    update_queue.add(task)


def gettrk(name):
    d = allinfo() # XXX allinfo is not reliable and might miss trackers.
    a = [t for t in d if ('name' in d[t] and d[t]['name'] == name)]
    if len(a) == 1:
        return (a[0], d[a[0]])
    elif len(a) == 0:
        return (None, None)
    else:
        return "Error: More than one tracker with same name!"
        

def getlogs(t):

    l = MC.get(t, namespace='logs') or []
    if not l:
        return []

    return sorted(MC.get_multi(["%s!%d" % (t, tm) for tm in l], namespace='logs').values(), key=(lambda x: x['updated'] or ''), reverse=True)

