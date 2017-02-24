import logging
import threading
from logging import FileHandler

from bottle import Bottle, run, static_file, request, response, abort, mako_template as template
from requestlogger import WSGILogger, ApacheFormatter

import trackon
import trackerlist_project

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
    trackers_list = trackon.get_main_from_db()
    return template('tpl/main.mako', trackers=trackers_list)


@app.route('/', method='POST')
def new_tracker():
    new_ts = request.forms.get('tracker-address')
    check_all_trackers = threading.Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return main()


@app.route('/incoming-log')
def incoming():
    size, incoming150 = trackon.get_150_incoming()
    if size == 0:
        incoming150 = ''
    return template('tpl/incoming-log.mako', incoming=incoming150, size=size)


@app.route('/faq')
def faq():
    return template('tpl/static/faq.mako')


def list_uptime(uptime):
    trackers_list = trackon.get_main_from_db()
    formatted_list = ''
    length = 0
    for t in trackers_list:
        if t.uptime >= uptime:
            length += 1
            formatted_list += t.url + '\n' + '\n'
    return formatted_list, length


def list_live():
    trackers_list = trackon.get_main_from_db()
    list = ''
    for t in trackers_list:
        if t.status == 1:
            list += t.url + '\n' + '\n'
    return list


@app.route('/list')
def list_stable():
    stable_list, size = list_uptime(95)
    return template('tpl/list.mako', stable=stable_list, size=size)


@app.route('/api')
def api():
    return template('tpl/static/api-docs.mako')

@app.route('/raw')
def raw():
    return template('tpl/raw.mako', data=trackon.raw_data)

@app.route('/api/<percentage:int>')
def api_percentage(percentage):
    if 0 <= percentage <= 100:
        response.content_type = 'text/plain'
        formatted_list, not_needed_length = list_uptime(percentage)
        return formatted_list
    else:
        abort(400, "The percentage has to be between 0 an 100")


@app.route('/api/best')
def api_best():
    return api_percentage(95)


@app.route('/api/all')
def api_all():
    return api_percentage(0)


@app.route('/api/live')
def api_live():
    response.content_type = 'text/plain'
    return list_live()


@app.route('/about')
def about():
    return template('tpl/static/about.mako')


@app.route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')

@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root='static/imgs')

update_status = threading.Thread(target=trackon.update_outdated_trackers)
update_status.daemon = True
update_status.start()

get_trackerlist_project_list = threading.Thread(target=trackerlist_project.main)
get_trackerlist_project_list.daemon = True
get_trackerlist_project_list.start()

handlers = [FileHandler('access.log'), ]
app = WSGILogger(app, handlers, ApacheFormatter())

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8080, server='waitress')
