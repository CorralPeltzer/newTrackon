from hashlib import md5
from google.appengine.api.urlfetch import fetch
from google.appengine.api import memcache as mc
from time import time
from bencode import bdecode

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
    except:
        return (False, "Error during fetch!", requrl)

    if r.status_code != 200:
        return (False, "Got HTTP code: %d" % r.status_code, requrl)
    
    if not r.content:
        return (False, "Got empty response.", requrl)

    try:
        be = bdecode(r.content)
    except:
        return (False, "Couldn't bdecode response: %s." % r.content, requrl)

    if 'failure reason' in be:
        return (False, "Tracker failure reason: %s." % be['failure reason'], requrl)
    # TODO Do a more extensive check of what was returned

    return (True, {'response': be, 'latency': latency } , requrl) 

def add(addr, info):
    l = mc.get('tracker-list')
    if not l:
        l = []
    
    l.append(addr)
    mc.set('tracker-list', l)
    if info:
        mc.set(addr, info)

##############################
class Tracker(object):
    def __init__(self, announce, name=None, homepage=None):
        self.announce = announce
        self.name = name
        if not name:
            self.name = announce # Todo - extract domain name
