from hashlib import md5
from google.appengine.api.urlfetch import fetch, Error as FetchError, DownloadError
from google.appengine.api import memcache as mc
from time import time
from trackon.bencode import bdecode
from google.appengine.api.labs import taskqueue as tq

update_queue = tq.Queue('update-trackers')
new_queue = tq.Queue('new-trackers')

def trackerhash(addr):
    """Generate a 'fake' info_hash to be used with this tracker."""
    return md5(addr).hexdigest()[:20]

def genqstr(h):
    peerid = "-TO0001-XX"+str(int(time())) # 'random' peer id
    return "?info_hash=%s&port=999&peer_id=%s" % (h, peerid)

def check(addr):
    """Check if a tracker is up."""
    thash = trackerhash(addr) # The info_hash we will use for this tracker 
    requrl = addr+genqstr(thash)
    d = {}
    try:
        t1 = time()
        r = fetch(requrl, deadline=10)
        d['latency'] = time() - t1
    except DownloadError, e:
        d['error'] = "Could not reach tracker." # XXX Should find out why!
    except FetchError, e:
        d['error'] = "Fetchurl error: %s" % repr(e)
    
    if 'error' in d:
        d['latency'] = time() - t1
        return (d, requrl)


    if r.status_code != 200:
        d['error'] = "Unexpected HTTP status: %d" % r.status_code
    
    elif not r.content:
        d['error'] = "Got empty HTTP response."

    else:
        try:
            d['response'] = bdecode(r.content)
        except:
            d['error'] = "Couldn't bdecode response: %s." % r.content

    if 'response' in d:
        if 'failure reason' in d['response']:
            d['error'] = "Tracker failure reason: %s." % d['response']['failure reason']
        elif 'peers' not in d['response']:
            d['error'] = "Invalid response, 'peers' field is missing!"

    # TODO Do a more extensive check of what was returned

    return (d, requrl) 


def update(t, info):
    tim = int(time())
    info['updated'] = tim
    mc.set(t, info, namespace="status")

    # Status log 
    mc.set("%s!%d" % (t, tim), info, namespace="logs")
    l = mc.get(t, namespace="logs") or []
    l.insert(0, tim)
    mc.set(t, l[:64], namespace="logs") # Keep 64 samples

def add(t, info):
    l = mc.get('tracker-list') or []
    l.append(t) # XXX Rare race, we avoid it by having a single task in bucket.
    mc.set('tracker-list', l)

    update(t, info)

def new(t):
    task = tq.Task(params={'tracker-address': t, 'attempts': 0})
    new_queue.add(task)

def allinfo():
    tl = mc.get('tracker-list')
    ts = {}
    if tl:
        ts = mc.get_multi(tl, namespace='status')

    return ts
