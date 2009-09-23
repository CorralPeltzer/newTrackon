from hashlib import md5
from google.appengine.api.urlfetch import fetch, Error as FetchError
from google.appengine.api import memcache as mc
from time import time
from bencode import bdecode
from google.appengine.api.labs import taskqueue as tq

update_queue = tq.Queue('update-trackers')

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
    try:
        t1 = time()
        r = fetch(requrl, deadline=10)
        t2 = time()
        latency = t2 - t1
    except FetchError, e:
        return ({'error': "Fetchurl error: %s" % str(e)}, requrl)

    if r.status_code != 200:
        return ({'error': "Unexpected HTTP status: %d" % r.status_code}, requrl)
    
    if not r.content:
        return ({'error': "Got empty HTTP response."}, requrl)

    try:
        be = bdecode(r.content)
    except:
        return ({'error': "Couldn't bdecode response: %s." % r.content}, requrl)

    if 'failure reason' in be:
        return ({'error': "Tracker failure reason: %s." % be['failure reason']}, requrl)
    # TODO Do a more extensive check of what was returned

    return ({'response': be, 'latency': latency } , requrl) 


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
    l.append(t) # XXX Rare race, plus we avoid it by having a single task in bucket.
    mc.set('tracker-list', l)

    update(t, info)
    #params = {'tracker-address': addr}
    #task = tq.Task(params=params)
    #update_queue.add(task)

##############################
class Tracker(object):
    def __init__(self, announce, name=None, homepage=None):
        self.announce = announce
        self.name = name
        if not name:
            self.name = announce # Todo - extract domain name
