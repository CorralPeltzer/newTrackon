from google.appengine.api import memcache as MC


def logmsg(msg, log_name='default'):
    # TODO Should optimize to avoid memcache's pickling
    # XXX There is an obvious race if we try to store two msgs at the same time
    l = MC.get(log_name, namespace='msg-logs') or []
    l.insert(0, msg)
    MC.set(log_name, l[:64], namespace='msg-logs') # Keep 64 messages

def getmsglog(log_name='default'):
    return MC.get(log_name, namespace='msg-logs')

