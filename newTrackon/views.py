from logging import FileHandler, getLogger, INFO, Formatter
from threading import Thread

from flask import (
    Flask,
    send_from_directory,
    request,
    Response,
    redirect,
    make_response,
    abort,
)
from flask_mako import MakoTemplates, render_template
from werkzeug.routing import BaseConverter

from newTrackon import db, utils, trackon


mako = MakoTemplates()
app = Flask(__name__)
app.template_folder = 'tpl'
mako.init_app(app)


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app.url_map.converters["regex"] = RegexConverter
logger = getLogger("newtrackon_logger")
logger.setLevel(INFO)
handler = FileHandler("data/trackon.log")
logger_format = Formatter("%(asctime)s - %(message)s")
handler.setFormatter(logger_format)
logger.addHandler(handler)
logger.info("Server started")


@app.route("/")
def main():
    trackers_list = db.get_all_data()
    trackers_list = utils.process_uptime_and_downtime_time(trackers_list)
    return render_template("main.mako", trackers=trackers_list, active="main")


@app.route("/", methods=["POST"])
def new_trackers():
    new_ts = request.form.get("new_trackers")
    check_all_trackers = Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    return main()


@app.route("/api/add", methods=["POST"])
def new_trackers_api():
    new_ts = request.form.get("new_trackers")
    check_all_trackers = Thread(target=trackon.enqueue_new_trackers, args=(new_ts,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    resp = Response(status=204, headers={"Access-Control-Allow-Origin": "*"})
    return resp


@app.route("/submitted")
def submitted():
    return render_template(
        "submitted.mako",
        data=trackon.submitted_data,
        size=len(trackon.submitted_trackers),
        active="submitted",
    )


@app.route("/faq")
def faq():
    return render_template("/static/faq.mako", active="faq")


@app.route("/list")
def list_stable():
    return render_template("/static/list.mako", active="list")


@app.route("/api")
def api_docs():
    return render_template("/static/api-docs.mako", active="api")


@app.route("/raw")
def raw():
    return render_template("raw.mako", data=trackon.raw_data, active="raw")


@app.route("/api/<int:percentage>")
def api_percentage(percentage):
    include_upv6_only = (
        False
        if request.args.get("include_ipv6_only_trackers") in ("False", "0")
        else True
    )
    if 0 <= percentage <= 100:
        formatted_list = db.get_api_data(
            "percentage", percentage, include_upv6_only
        )
        resp = make_response(formatted_list)
        resp = utils.add_api_headers(resp)
        return resp
    else:
        abort(
            Response(
                "The percentage has to be between 0 an 100",
                400,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        )


@app.route("/api/stable")
def api_stable():
    return api_percentage(95)


@app.route("/api/best")
def api_best():
    return redirect("/api/stable", code=301)


@app.route("/api/all")
def api_all():
    return api_percentage(0)


@app.route("/api/live")
@app.route("/api/udp")
@app.route("/api/http")
def api_multiple():
    resp = make_response(db.get_api_data(request.path))
    resp = utils.add_api_headers(resp)
    return resp


@app.route("/about")
def about():
    return render_template("/static/about.mako", active="about")


@app.route(
    '/<regex(".*(?=\.)"):filename>.<regex("(png|svg|ico)"):filetype>'
)  # matches all favicons that should be in root
def favicon(filename, filetype):
    return send_from_directory("static/imgs/", filename + "." + filetype)


@app.route(
    '/<regex(".*(?=\.)"):filename>.<regex("(xml|json)"):filetype>'
)  # matches browserconfig and manifest that should be in root
def app_things(filename, filetype):
    return send_from_directory("static/", filename + "." + filetype)
