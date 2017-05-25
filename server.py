import logging
import threading
from logging import FileHandler
from bottle import Bottle, run, static_file, request, response, HTTPError, redirect, mako_template as template
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
    trackers_list = trackon.get_all_data_from_db()
    return template('tpl/main.mako', trackers=trackers_list, active='main')


@app.route('/', method='POST')
def new_trackers():
    new_ts = request.forms.get('new_trackers')
    check_all_trackers = threading.Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return main()


@app.route('/api/add', method='POST')
def new_trackers_api():
    response.set_header("Access-Control-Allow-Origin", "*")
    new_ts = request.forms.get('new_trackers')
    check_all_trackers = threading.Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    response.status = 204
    return response


@app.route('/submitted')
def submitted():
    return template('tpl/submitted.mako', data=trackon.submitted_data, size=len(trackon.submitted_trackers), active='submitted')


@app.route('/faq')
def faq():
    return template('tpl/static/faq.mako', active='faq')


@app.route('/list')
def list_stable():
    stable_list, size = trackon.list_uptime(95)
    return template('tpl/list.mako', stable=stable_list, size=size, active='list')


@app.route('/api')
def api():
    return template('tpl/static/api-docs.mako', active='api')


@app.route('/raw')
def raw():
    return template('tpl/raw.mako', data=trackon.raw_data, active='raw')


@app.route('/api/<percentage:int>')
def api_percentage(percentage):
    if 0 <= percentage <= 100:
        add_api_headers()
        formatted_list, not_needed_length = trackon.list_uptime(percentage)
        return formatted_list
    else:
        # abort(400, "The percentage has to be between 0 an 100") Abort does not allow custom headers
        raise HTTPError(status=400, body="The percentage has to be between 0 an 100", headers={"Access-Control-Allow-Origin": "*"})


@app.route('/api/stable')
def api_stable():
    return api_percentage(95)


@app.route('/api/all')
def api_all():
    return api_percentage(0)


@app.route('/api/live')
def api_live():
    add_api_headers()
    return trackon.list_live()


@app.route('/api/udp')
def api_udp():
    add_api_headers()
    return trackon.api_udp()


@app.route('/api/http')
def api_http():
    add_api_headers()
    return trackon.api_http()


@app.route('/about')
def about():
    return template('tpl/static/about.mako', active='about')


@app.route('/static/<path:path>')  # matches any static file
def static(path):
    return static_file(path, root='static')


@app.route('/<filename>.<filetype:re:(png|svg|ico)>')  # matches all favicons that should be in root
def favicon(filename, filetype):
    response.content_type = 'image/x-icon'
    return static_file(filename + '.' + filetype, root='static/imgs')


@app.route('/<filename>.<filetype:re:(xml|json)>')  # matches browserconfig and manifest that should be in root
def app_things(filename, filetype):
    return static_file(filename + '.' + filetype, root='static')


@app.hook('after_request')
def check_host_http_header():
    accepted_hosts = {'localhost:8080', 'localhost', '127.0.0.1:8080', '127.0.0.1'}
    if request.headers['host'] not in accepted_hosts:
        redirect('http://localhost:8080/', 301)


def add_api_headers():
    response.set_header("Access-Control-Allow-Origin", "*")
    response.content_type = 'text/plain'

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
