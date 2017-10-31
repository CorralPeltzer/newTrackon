from threading import Thread
from logging import FileHandler, getLogger
from flask import Flask, send_from_directory, request, Response, redirect, make_response, abort
from flask_mako import MakoTemplates, render_template
from werkzeug.routing import BaseConverter
from requestlogger import WSGILogger, ApacheFormatter
from cheroot.wsgi import Server

import trackon
import trackerlist_project

mako = MakoTemplates()
app = Flask(__name__)
app.template_folder = "tpl"
mako.init_app(app)


accepted_hosts = {'localhost:8080', 'localhost', '127.0.0.1', '127.0.0.1:8080'}
canonical_url = 'http://localhost:8080/'


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app.url_map.converters['regex'] = RegexConverter
logger = getLogger('trackon_logger')
logger.info('Server started')


@app.route('/')
def main():
    trackers_list = trackon.get_all_data_from_db()
    trackers_list = trackon.process_uptime_and_downtime_time(trackers_list)
    return render_template('main.mako', trackers=trackers_list, active='main')


@app.route('/', methods=['POST'])
def new_trackers():
    new_ts = request.form.get('new_trackers')
    check_all_trackers = Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return main()


@app.route('/api/add', methods=['POST'])
def new_trackers_api():
    new_ts = request.form.get('new_trackers')
    check_all_trackers = Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    resp = Response(status=204, headers={'Access-Control-Allow-Origin': '*'})
    return resp


@app.route('/submitted')
def submitted():
    return render_template('submitted.mako', data=trackon.submitted_data, size=len(trackon.submitted_trackers), active='submitted')


@app.route('/faq')
def faq():
    return render_template('/static/faq.mako', active='faq')


@app.route('/list')
def list_stable():
    stable_list, size = trackon.list_uptime(95)
    return render_template('list.mako', stable=stable_list, size=size, active='list')


@app.route('/api')
def api():
    return render_template('/static/api-docs.mako', active='api')


@app.route('/raw')
def raw():
    return render_template('raw.mako', data=trackon.raw_data, active='raw')


@app.route('/api/<int:percentage>')
def api_percentage(percentage):
    if 0 <= percentage <= 100:
        formatted_list, not_needed_length = trackon.list_uptime(percentage)
        resp = make_response(formatted_list)
        resp = add_api_headers(resp)
        return resp
    else:
        abort(Response("The percentage has to be between 0 an 100", 400, headers={'Access-Control-Allow-Origin': '*'}))


@app.route('/api/stable')
def api_stable():
    return api_percentage(95)


@app.route('/api/all')
def api_all():
    return api_percentage(0)


@app.route('/api/live')
def api_live():
    resp = make_response(trackon.list_live())
    resp = add_api_headers(resp)
    return resp


@app.route('/api/udp')
def api_udp():
    resp = make_response(trackon.api_udp())
    resp = add_api_headers(resp)
    return resp


@app.route('/api/http')
def api_http():
    resp = make_response(trackon.api_http())
    resp = add_api_headers(resp)
    return resp


@app.route('/about')
def about():
    return render_template('/static/about.mako', active='about')


@app.route('/<regex(".*(?=\.)"):filename>.<regex("(png|svg|ico)"):filetype>')  # matches all favicons that should be in root
def favicon(filename, filetype):
    return send_from_directory('static/imgs/', filename + '.' + filetype)


@app.route('/<regex(".*(?=\.)"):filename>.<regex("(xml|json)"):filetype>') # matches browserconfig and manifest that should be in root
def app_things(filename, filetype):
    return send_from_directory('static/', filename + '.' + filetype)


@app.before_request
def check_host_http_header():
    if request.headers.get('host') not in accepted_hosts:
        return redirect(canonical_url, code=301)


def add_api_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.mimetype = 'text/plain'
    return resp


update_status = Thread(target=trackon.update_outdated_trackers)
update_status.daemon = True
update_status.start()

get_trackerlist_project_list = Thread(target=trackerlist_project.main)
get_trackerlist_project_list.daemon = True
get_trackerlist_project_list.start()

handlers = [FileHandler('access.log'), ]
app = WSGILogger(app, handlers, ApacheFormatter())

server = Server(('0.0.0.0', 8080), app)

if __name__ == '__main__':
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()