from cgi import parse_qs, FieldStorage
from logging import debug, error, info
from google.appengine.api import memcache as mc
from google.appengine.api.labs import taskqueue as tq
from time import gmtime, time

"""
Trackon
"""

DEBUG = True
new_trackers_queue = tq.Queue('new-trackers')

def rndrtracker(t):
    s = mc.get(t, namespace="status")
    if not s:
        error("Tracker in tracker-list but no status: %s"%t)
        return

    def cell(s):
        if s:
            print "<td>%s</td>" % s
        else:
            print "<td>-</td>" % s


    cell(t.split('/')[2]) # Domain ('Tracker')
    cell("%.3f"%s['latency'])
    cell("%dm ago" % ((int(time()) - s['updated']) / 60) )
    if 'error' in s:
        cell('<b title="%s">Error!</b>'%s['error']) # Possible injection!
        cell('-')
        cell('-')
        cell('-')
    else:
        r = s['response']
        cell('<b>UP!</b>')
        cell(r['interval'])
        cell("<a href='%s' title=>Link</a>"%t)
        #cell("%d/%d/%d %d:%d:%d"%(gmtime(s['updated'])[:6]))
        cell(repr(r))
    


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
        print "Location: /"
        print ""
        return


    def html():
        print "<h1><i>Trackon <b><small>Pre-Alpha 2</small></b></i></h1>"
        tl = mc.get('tracker-list')
        if tl:
            print "<table cellspacing=0 class='sortable'>"
            print "<thead><tr><th>Tracker</th><th>Latency</th><th>Checked</th><th>Up?</th><th>Interval</th><th>Announce</th><th>...</th></tr></thead>"
            for t in tl:
                print "<tr>"
                rndrtracker(t)
                print "</tr>"

        print "</table>"
        print "<br>"
        print """<form method="POST"><input type="text" name="tracker-address" value="" size=64><input type="submit" value="Add Tracker"></form>"""

        print "<p>Extremely experimental, <b>please do not post to torrent freak or any public forum yet! ;)</b></p>"
        print "<p>If you post a new tracker, please allow for a few minutes while we gather statistics before it is added to the list.</p>"
        print "<p><a href='http://uriel.cat-v.org/contact'>Contact for comments and bug reports</a>.</p>"
        print "<br><img src='http://upload.wikimedia.org/wikipedia/commons/3/3e/Nine-Dragons1.jpg' title='The Trackon' alt='The Trackon' />"

    rndpage(html)


def rndpage(f):
    print """Content-type: text/html

<!DOCTYPE HTML>
<html>
<head>
<title>The Trackons Lair</title>
<link rel="stylesheet" href="/static/style.css" type="text/css" />
<script type="text/javascript" src="http://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
</head>
<body>"""

    f()
    print """</body></html>"""


if __name__ == '__main__':
    main()
