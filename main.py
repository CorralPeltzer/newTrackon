from cgi import parse_qs, FieldStorage
from logging import debug, error, info
from google.appengine.api import memcache as mc
from google.appengine.api.labs import taskqueue as tq

"""
Trackon
"""

DEBUG = True
new_trackers_queue = tq.Queue('new-trackers')

def rndrtracker(t):
    s = mc.get(t, namespace="status")
    if not s:
        print "XXXX"
        return

    def cell(s):
        if s:
            print "<td>%s</td>" % s
        else:
            print "<td>-</td>" % s

    r = s['response']
    cell(t)
    cell(s['latency'])
    cell(r['interval'])
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

    def html():
        tl = mc.get('tracker-list')
        if tl:
            print "<table class='sortable'>"
            print "<thead><tr><th>Addres</th><th>Latency</th><th>Interval</th><th>...</th></tr></thead>"
            for t in tl:
                print "<tr>"
                rndrtracker(t)
                print "</tr>"
                #print "<tr><td>%s - %s</td></tr>\n" % (t, mc.get(t))

        print "</table>"

        print """<form method="POST"><input type="text" name="tracker-address" value="" size=64><input type="submit" value="Add Tracker"></form>"""

    rndpage(html)


def rndpage(f):
    print """Content-type: text/html

<!DOCTYPE HTML>
<html>
<head>
<script type="text/javascript" src="http://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
<style>
table.sortable thead {
    background-color:#eee;
    color:#666666;
    font-weight: bold;
    cursor: default;
}
</style>
</head>
<body>"""

    f()
    print """</body></html>"""


if __name__ == '__main__':
    main()
