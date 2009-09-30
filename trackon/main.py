from cgi import FieldStorage
from trackon import tracker
from trackon.web import renderpage, postredir

"""
Trackon
"""

def main():
     
    new_tracker_error = None
    req = FieldStorage()
    if 'tracker-address' in req:
        from urlparse import urlparse 
        trdrs = req['tracker-address'].value.split()
        for t in trdrs:
            u = urlparse(t)
            if (u.scheme in ['http', 'https']) and u.netloc and u.path:
                if u.port and u.port not in [80, 443]:
                    new_tracker_error = "Only trackers running on ports 80 or 443 are supported!"
                else:
                    t = "%s://%s%s" % (u.scheme, u.netloc, u.path)
                    # XXX Need some kind of rate-limiting to avoid abuse / DoS
                    tracker.incoming(t)
            else:
                new_tracker_error = "Invalid URL!"

        if not new_tracker_error:
            postredir('/incoming-log')
            return

    ts = tracker.allinfo() 
    renderpage('main', trackers=ts, new_tracker_error=new_tracker_error)


if __name__ == '__main__':
    main()
