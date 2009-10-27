from google.appengine.api import memcache as MC
from google.appengine.api import datastore as DS

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from mako.template import Template
from mako.lookup import TemplateLookup

from trackon.gaeutils import logmsg, getentity

from trackon import tracker

tpl_lookup = TemplateLookup(directories=['../tpl/'])

class AdminPage(webapp.RequestHandler):
    def get(self):
        req = self.request
        write = self.response.out.write

        tpl = tpl_lookup.get_template('admin.mako')
        write(tpl.render(trackers_info=tracker.allinfo()))

    def post(self):
        req = self.request

        act = req.get('action')
        t = req.get('address')
        if act == 'New':
            if t:
                i = tracker.check(t)[0]
                tracker.add(t, i)

        elif act == 'Update':
            if t:
                e = getentity('Tracker', t) or DS.Entity('Tracker', name=t)
                s = MC.get(t, namespace='status') or {}
                if req.get('title'):
                    e['title'] = req.get('title')
                    s['title'] = req.get('title')
                if req.get('home') is not None: # We allow '' to mean 'no home'.
                    e['home'] = req.get('home')
                    s['home'] = req.get('home')
                if req.get('name') is not None: # We allow '' to mean 'no home'.
                    e['name'] = req.get('name')
                    s['name'] = req.get('name')
                MC.set(t, s, namespace='status') # XXX Race with update()
                DS.Put(e)
        
        elif act == 'Delete':
            if t:
                tracker.delete(t)

        self.redirect('/admin')


application = webapp.WSGIApplication([('/admin', AdminPage)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

