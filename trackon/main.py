from cgi import FieldStorage
from google.appengine.api import memcache as mc
from google.appengine.api.labs import taskqueue as tq
from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import html_error_template
from trackon import tracker

"""
Trackon
"""

DEBUG = True
tpl_lookup = TemplateLookup(directories=['../tpl/'])
#tpl_main = tpl_lookup.get_template('main.mako')


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
                    tracker.new(t)
            else:
                new_tracker_error = "Invalid URL!"

        if not new_tracker_error:
            print "Status: 303 See Other"
            print "Location: /\n"
            return


    print "Content-type: text/html\n"
    tl = mc.get('tracker-list')
    ts = {}
    if tl:
        ts = mc.get_multi(tl, namespace='status')


    try:
        tpl_main = tpl_lookup.get_template('main.mako') # TODO: cache
        print tpl_main.render(trackers=ts, new_tracker_error=new_tracker_error)
    except:
        print html_error_template().render()


if __name__ == '__main__':
    main()
