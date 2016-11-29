import tracker
from bottle import route, run, static_file, request, mako_template as template
import threading


@route('/')
def main():
    trackers_list = tracker.get_trackers_status()

    return template('tpl/main.mako', trackers=trackers_list)

@route('/', method='POST')
def newTracker():
    new_ts = request.forms.get('tracker-address')
    trackers_list = tracker.get_trackers_status()
    check_all_trackers = threading.Thread(target=tracker.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return template('tpl/main.mako', trackers=trackers_list)

@route('/incoming-log')
def incoming():
    size, incoming150 = tracker.get_150_incoming()
    if size==0:
        incoming150 = ''
    return template('tpl/incoming-log.mako', incoming=incoming150, size=size)

@route('/list')
def list():
    trackers_list = tracker.get_trackers_status()
    list = ''
    for t in trackers_list:
        if t['uptime'] >= 90:
            list += t['url'] + '\n' + '\n'
    return template('tpl/list.mako', list=list)

@route('/faq')
def faq():
    return template('tpl/static/faq.mako')

@route('/about')
def about():
    return template('tpl/static/about.mako')

@route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')


update_status = threading.Thread(target=tracker.update_status)
update_status.daemon = True
update_status.start()
run(host='0.0.0.0', port=8080, server='paste')
