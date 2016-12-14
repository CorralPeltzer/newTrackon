import tracker
import trackerlist_project
from bottle import Bottle, run, static_file, request, response, abort, mako_template as template
import threading
import logging
from requestlogger import WSGILogger, ApacheFormatter
from logging import FileHandler

app = Bottle()

logger = logging.getLogger('trackon_logger')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('trackon.log')
logger_format = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(logger_format)
logger.addHandler(handler)

logger.info('Server started')


@app.route('/')
def main():
    trackers_list = tracker.get_trackers_status()
    return template('tpl/main.mako', trackers=trackers_list)


@app.route('/', method='POST')
def new_tracker():
    new_ts = request.forms.get('tracker-address')
    trackers_list = tracker.get_trackers_status()
    check_all_trackers = threading.Thread(target=tracker.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return template('tpl/main.mako', trackers=trackers_list)


@app.route('/incoming-log')
def incoming():
    size, incoming150 = tracker.get_150_incoming()
    if size == 0:
        incoming150 = ''
    return template('tpl/incoming-log.mako', incoming=incoming150, size=size)


def _list(uptime):
    trackers_list = tracker.get_trackers_status()
    list = ''
    for t in trackers_list:
        if t['uptime'] >= uptime:
            list += t['url'] + '\n' + '\n'
    return list


@app.route('/list')
def list():
    return template('tpl/list.mako', list=_list(95))


@app.route('/api/<percentage:int>')
def api_percentage(percentage):
    if 0 <= percentage <= 100:
        response.content_type = 'text/plain'
        return _list(percentage)
    else:
        abort(400, "The percentage has to be between 0 an 100")


@app.route('/api/best')
def api_best():
    return api_percentage(95)


@app.route('/api/all')
def api_all():
    return api_percentage(0)


@app.route('/faq')
def faq():
    return template('tpl/static/faq.mako')


@app.route('/about')
def about():
    return template('tpl/static/about.mako')


@app.route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')


update_status = threading.Thread(target=tracker.update_status)
update_status.daemon = True
update_status.start()

get_trackerlist_project_list = threading.Thread(target=trackerlist_project.main)
get_trackerlist_project_list.daemon = True
get_trackerlist_project_list.start()

handlers = [FileHandler('access.log'), ]
app = WSGILogger(app, handlers, ApacheFormatter())

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8080, server='paste')

