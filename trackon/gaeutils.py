from google.appengine.api import datastore as DS
from google.appengine.api import memcache as MC
from google.appengine.api.datastore_errors import EntityNotFoundError
from time import gmtime


def logmsg(msg, log_name='default'):
    # TODO Should optimize to avoid memcache's pickling
    # XXX There is an obvious race if we try to store two msgs at the same time
    l = MC.get(log_name, namespace='msg-logs') or []
    d = "%d/%02d/%02d %02d:%02d" % (gmtime()[:5])
    l.insert(0, "%s - %s" %(d, msg))
    MC.set(log_name, l[:128], namespace='msg-logs') # Keep 64 messages

def getmsglog(log_name='default'):
    return MC.get(log_name, namespace='msg-logs')

def getentity(kind, id):
    """ Get entity by name/id (name if string, 'id' if int). """
    try:
        return DS.Get(DS.Key.from_path(kind, id))
    except EntityNotFoundError, e:
        return None

