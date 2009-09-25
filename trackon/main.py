from time import time
from cgi import FieldStorage
from logging import error
from google.appengine.api import memcache as mc
from google.appengine.api.labs import taskqueue as tq
from mako.template import Template
from mako.lookup import TemplateLookup

"""
Trackon
"""

DEBUG = True
new_trackers_queue = tq.Queue('new-trackers')
tpl_lookup = TemplateLookup(directories=['../tpl/'])
#tpl_main = tpl_lookup.get_template('main.mako')


def main():
     
    req = FieldStorage()
    if 'tracker-address' in req:
        trdrs = req['tracker-address'].value.split()
        for t in trdrs:
            # TODO: perhaps validate that we got at least a valid url?
            # XXX Need some kind of rate-limiting to avoid abuse / DoS
            task = tq.Task(params={'tracker-address': t, 'attempts': 0})
            new_trackers_queue.add(task)

        print "Status: 303 See Other"
        print "Location: /\n"
        return


    print "Content-type: text/html\n"
    tl = mc.get('tracker-list')
    ts = {}
    if tl:
        ts = mc.get_multi(tl, namespace='status')
        #ts = (t for t in mc.get_multi(tl, namespace='status') if t)
    error( repr(ts))

    from mako import exceptions

    try:
        #template = lookup.get_template(uri)
        #print template.render()
        tpl_main = tpl_lookup.get_template('main.mako')
        print tpl_main.render(trackers=ts)
    except:
        print exceptions.html_error_template().render()



if __name__ == '__main__':
    main()
