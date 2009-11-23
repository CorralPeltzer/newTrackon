from time import time
from os import environ
from cgi import parse_qs, FieldStorage as FormPost
import google.appengine.api.labs.taskqueue as tq
from google.appengine.api.memcache import get as mget, set as mset, get_multi as mmget, delete as mdel, flush_all
import google.appengine.api.memcache as m

NS = 'MESTAT-DATA'

def stat():
    """Save current stats"""
    s = m.get_stats()
    t = int(time())
    m.set(str(t), s, namespace=NS)

    # XXX Possible race if task scheduler messes up, but we don't care.
    sts = m.get('sample-times', namespace=NS)
    if sts == None:
        sts = []
    sts.insert(0, t)
    sts = sts[:2*6*24] # Keep two days of data (at a rate of one sample/10min )
    m.set('sample-times', sts, namespace=NS)


def main():

    args = parse_qs(environ['QUERY_STRING'])
    form = FormPost()
    if form.has_key('FLUSH'):
        flush_all()

    if 'update' in args:
        stat()
        return
    
    ats = ['items', 'bytes', 'oldest_item_age', 'hits', 'byte_hits', 'misses']
    samples = mget('sample-times', namespace=NS)
    if not samples:
        stat()
        samples = mget('sample-times', namespace=NS)

    s = mmget([str(i) for i in samples], namespace=NS)
    #  
    a = dict([(k, [int(s[d][k]) for d in s]) for k in ats]) # attr -> vals
    a = dict([(k, (max(a[k]), min(a[k]), a[k])) for k in a]) # attrs -> (max, min, vals)
    #a = dict([(k, [61*(v+1-a[k][1])/(a[k][0]+1-a[k][1]) for v in a[k][2]]) for k in a]) # attrs -> norml-vals
    a = dict([(k, ([61*(v+1-a[k][1])/(a[k][0]+1-a[k][1]) for v in a[k][2]], a[k][1], a[k][0])) for k in a]) # attrs -> norml-vals
    print "Content-type: text/html"
    print ""
    #l = ["rend('"+k+"', %s);"%str([int(s[d][k]) for d in s]) for k in ats]
    #l = ["rend('"+k+"', %s);"%str([int(d) for d in a[k]]) for k in a]
    print """<html><head><script type="text/javascript" src="http://www.solutoire.com/download/gchart/gchart-0.2alpha_uncompressed.js"></script>
<script>
// Using: http://solutoire.com/gchart/
// x = """+repr(a)+"""
function rend(t, d, mx, mn) {
GChart.render({'renderTo': 'stats', 'size': '800x200', colors: 'FF0000,00FF00,0000FF,FFFF00,00FFFF,FF00FF', legend:'"""+'|'.join([k for k in a])+"""',  title: t, 'data': d});
}
function main() {
"""
    def rnd(name, data, mxmn, colors, legend):
        print "GChart.render({'size': '480x200&chg=0,20', axistype: 'x,y,r'," # colors: 'FF0000,00FF00,0000FF,FFFF00,00FFFF,FF00FF',"
        print "     renderTo: '"+name+"',"
        if len(data) == 2:
            print "     axisrange: '1,"+','.join([str(i) for i in mxmn[0]])+"|2,"+','.join([str(i) for i in mxmn[1]])+"',"
        elif len(data) == 1:
            print "     axisrange: '1,"+','.join([str(i) for i in mxmn[0]])+"', axistype: 'x,y',"
        print "     colors: '"+','.join(colors)+"',"
        print "     legend:'"+'|'.join([l for l in legend])+"',"
        print "     data: "+str([[int(d) for d in dd] for dd in data])
        print "});"

    #print "rend('stats', %s);"%str([[int(d) for d in a[k][0]] for k in a])
    rnd('stats', [a['hits'][0], a['byte_hits'][0]], [a['hits'][1:3], a['byte_hits'][1:3]], ['FF0088', '0077cc'], ["Hits", "Hit Bytes"])
    rnd('stats', [a['items'][0], a['bytes'][0]], [a['items'][1:3], a['bytes'][1:3]], ['FF0088', '0077cc'], ["Items", "Bytes"])
    rnd('stats', [a['misses'][0]], [a['misses'][1:3]], ['FF0088'], ["Miss"])
    rnd('stats', [a['oldest_item_age'][0]], [[x/60 for x in a['oldest_item_age'][1:3]]], ['0077cc'], ["Max Age"])
    print """
}
</script>
</head><body onload="main();">
<h1>Memcache Stats</a>
<form action="" method="POST"><input type="submit" name="FLUSH" value="Flush Memcache!"></form>
<div id="stats"></div>
</body></html>
"""


if __name__ == '__main__':
    main()




