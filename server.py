import tracker
from bottle import Bottle, run, static_file, request, mako_template as template
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


@app.route('/list')
def get_list():
    trackers_list = tracker.get_trackers_status()
    list = ''
    for t in trackers_list:
        if t['uptime'] >= 95:
            list += t['url'] + '\n' + '\n'
    return template('tpl/list.mako', list=list)


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


handlers = [FileHandler('access.log'), ]
app = WSGILogger(app, handlers, ApacheFormatter())

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8080, server='paste')

