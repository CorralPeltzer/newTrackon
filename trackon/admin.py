from google.appengine.api import memcache as mc

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from mako.template import Template
from mako.lookup import TemplateLookup

from trackon import tracker

tpl_lookup = TemplateLookup(directories=['../tpl/'])

class AdminPage(webapp.RequestHandler):
  def get(self):
    write = self.response.out.write
    tpl = tpl_lookup.get_template('admin.mako')

    write(tpl.render(trackers_info=tracker.allinfo()))



application = webapp.WSGIApplication([('/admin', AdminPage)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

