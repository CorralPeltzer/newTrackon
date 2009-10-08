from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import html_error_template

tpl_lookup = TemplateLookup(directories=['../tpl/'], input_encoding='utf-8', output_encoding='utf-8', encoding_errors='replace')

def render(tpl, **d):
    """Render ../tpl/${tpl}.mako template."""
    # TODO Some kind of explicit in memory caching?
    try:
        tpl_main = tpl_lookup.get_template('%s.mako'%tpl) # TODO: cache
        print tpl_main.render(**d)
    except:
        print html_error_template().render()


def renderpage(tpl, **d):
    print "Content-type: text/html\n"
    render(tpl, **d)

def postredir(addr):
    print "Status: 303 See Other"
    print "Location: %s\n" % addr

def permredir(addr):
    print "Status: 301 Permanent Redirect"
    print "Location: %s\n" % addr



