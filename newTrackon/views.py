from datetime import UTC, datetime
from logging import ERROR, INFO, basicConfig, getLogger
from sys import stdout
from threading import Thread
from time import time

from flask import (
    Flask,
    Response,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from werkzeug.routing import BaseConverter, Map

from newTrackon import db, trackon, utils

max_input_length: int = 1000000

app = Flask(__name__)
app.template_folder = "tpl"


class RegexConverter(BaseConverter):
    def __init__(self, url_map: Map, *items: str) -> None:
        super().__init__(url_map)
        self.regex = items[0]


app.url_map.converters["regex"] = RegexConverter


@app.template_filter("format_timestamp")
def format_timestamp(timestamp: int | float | None) -> str:
    """Convert Unix timestamp to HH:MM:SS UTC format."""
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(timestamp, tz=UTC).strftime("%H:%M:%S UTC")


@app.template_filter("format_date")
def format_date(timestamp: int | float | None) -> str:
    """Convert Unix timestamp to D-M-YYYY date format."""
    if timestamp is None:
        return ""
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    return f"{dt.day}-{dt.month}-{dt.year}"


basicConfig(
    level=INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    stream=stdout,
)
logger = getLogger("newtrackon")
getLogger("urllib3").setLevel(ERROR)  # Suppress urllib3 warnings, some weird servers can trigger them
logger.info("Server started")


@app.route("/")
def main(form_feedback: str | None = None) -> str:
    trackers_list = db.get_all_data()
    trackers_list = utils.format_uptime_and_downtime_time(trackers_list)
    return render_template("main.jinja", form_feedback=form_feedback, trackers=trackers_list, active="Home")


@app.route("/", methods=["POST"])
def new_trackers():
    new_trackers = request.form.get("new_trackers")
    if new_trackers is None:
        abort(400)
    elif len(new_trackers) > max_input_length:
        abort(413)
    elif new_trackers == "":
        return main(form_feedback="EMPTY")
    else:
        check_all_trackers = Thread(target=trackon.enqueue_new_trackers, args=(new_trackers,))
        check_all_trackers.daemon = True
        check_all_trackers.start()
    return main(form_feedback="SUCCESS")


@app.route("/api/add", methods=["POST"])
def new_trackers_api():
    new_trackers = request.form.get("new_trackers")
    if not new_trackers:
        return abort(400)
    if len(new_trackers) > max_input_length:
        abort(413)
    check_all_trackers = Thread(target=trackon.enqueue_new_trackers, args=(new_trackers,))
    check_all_trackers.daemon = True
    check_all_trackers.start()
    resp = Response(status=204, headers={"Access-Control-Allow-Origin": "*"})
    return resp


@app.route("/submitted")
def submitted():
    return render_template(
        "submitted.jinja",
        # Iterating a deque while rendering can cause RuntimeError: deque mutated during iteration, so we cast it to a list
        data=list(trackon.submitted_data),
        size=len(trackon.submitted_trackers),
        active="Submitted",
    )


@app.route("/faq")
def faq():
    return render_template("/static/faq.jinja", active="FAQ")


@app.route("/list")
def list_stable():
    return render_template("/static/list.jinja", active="List")


@app.route("/api")
def api_docs():
    return render_template("/static/api-docs.jinja", active="API")


@app.route("/raw")
def raw():
    # Iterating a deque while rendering can cause RuntimeError: deque mutated during iteration, so we cast it to a list
    return render_template("raw.jinja", data=list(trackon.raw_data), active="Raw data")


@app.route("/api/<int:percentage>")
def api_percentage(percentage: int, added_before: int | None = None) -> Response:
    include_upv4_only = (
        False if request.args.get("include_ipv4_only_trackers", default="true").lower() in ("false", "0") else True
    )
    include_upv6_only = (
        False if request.args.get("include_ipv6_only_trackers", default="true").lower() in ("false", "0") else True
    )
    if 0 <= percentage <= 100:
        formatted_list = db.get_api_data("percentage", percentage, include_upv4_only, include_upv6_only, added_before)
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


stable_min_age: int = 10 * 86400  # 10 days in seconds


@app.route("/api/stable")
def api_stable():
    added_before = int(time()) - stable_min_age
    return api_percentage(95, added_before=added_before)


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
    return render_template("/static/about.jinja", active="About")


@app.route(r'/<regex(".*(?=\.)"):filename>.<regex("(png|svg|ico)"):filetype>')  # matches all favicons that should be in root
def favicon(filename: str, filetype: str) -> Response:
    return send_from_directory("static/imgs/", filename + "." + filetype)


@app.route(
    r'/<regex(".*(?=\.)"):filename>.<regex("(xml|json)"):filetype>'
)  # matches browserconfig and manifest that should be in root
def app_things(filename: str, filetype: str) -> Response:
    return send_from_directory("static/", filename + "." + filetype)


@app.route("/api.yml")
def openapi_def():
    return send_from_directory(".", "newtrackon-api.yml")


@app.before_request
def reject_announce_requests():
    if request.args.get("info_hash"):
        return abort(Response("newTrackon is not a tracker and cannot provide peers", 403))
