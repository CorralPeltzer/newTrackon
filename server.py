import logging
import threading
from logging import FileHandler

from bottle import Bottle, run, static_file, request, response, abort, mako_template as template
from requestlogger import WSGILogger, ApacheFormatter
import pprint
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
    trackers_list = trackon.get_all_data_from_db()
    return template('tpl/main.mako', trackers=trackers_list)


@app.route('/', method='POST')
def new_tracker():
    new_ts = request.forms.get('tracker-address')
    check_all_trackers = threading.Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return main()


@app.route('/submitted')
def submitted():
    size, submitted150 = trackon.get_150_submitted()
    if size == 0:
        submitted150 = ''
    return template('tpl/submitted.mako', submitted=submitted150, size=size)


@app.route('/faq')
def faq():
    return template('tpl/static/faq.mako')


@app.route('/list')
def list_stable():
    stable_list, size = trackon.list_uptime(95)
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
        formatted_list, not_needed_length = trackon.list_uptime(percentage)
        return formatted_list
    else:
        abort(400, "The percentage has to be between 0 an 100")


@app.route('/api/stable')
def api_stable():
    return api_percentage(95)


@app.route('/api/all')
def api_all():
    return api_percentage(0)


@app.route('/api/live')
def api_live():
    response.content_type = 'text/plain'
    return trackon.list_live()


@app.route('/api/udp')
def api_udp():
    response.content_type = 'text/plain'
    return trackon.list_udp()


@app.route('/api/http')
def api_http():
    response.content_type = 'text/plain'
    return trackon.list_http()


@app.route('/about')
def about():
    return template('tpl/static/about.mako')


@app.route('/static/:path#.+#', name='static')
def static(path):
    return static_file(path, root='static')


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root='static/imgs')


@app.hook('after_request')
def check_host_http_header():
    print(request.headers['host'])
    accepted_hosts = {'localhost:8080', 'localhost', '127.0.0.1:8080', '127.0.0.1'}
    if request.headers['host'] not in accepted_hosts:
        abort(404, "This site can only be found in localhost:8080")

update_status = threading.Thread(target=trackon.update_outdated_trackers)
update_status.daemon = True
update_status.start()

get_trackerlist_project_list = threading.Thread(target=trackerlist_project.main)
get_trackerlist_project_list.daemon = True
get_trackerlist_project_list.start()

handlers = [FileHandler('access.log'), ]
app = WSGILogger(app, handlers, ApacheFormatter())

if __name__ == '__main__':
    run(app, host='localhost', port=8080, server='waitress')
