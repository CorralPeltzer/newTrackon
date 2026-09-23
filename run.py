import argparse
from threading import Thread
from typing import cast

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer

from newtrackon import db, ingest, scraper, trackerlist_project, trackon
from newtrackon.scraper import get_server_ip
from newtrackon.views import app


class Arguments(argparse.Namespace):
    address: str = "localhost"
    port: int = 8080
    ignore_ipv4: bool = False
    ignore_ipv6: bool = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--address", type=str, help="Address for the flask server", default="localhost")
    _ = parser.add_argument("--port", type=int, help="Port for the flask server", default=8080)
    _ = parser.add_argument(
        "--ignore-ipv4",
        help="Ignore newTrackon server IPv4 detection",
        dest="ignore_ipv4",
        action="store_true",
    )
    _ = parser.add_argument(
        "--ignore-ipv6",
        help="Ignore newTrackon server IPv6 detection",
        dest="ignore_ipv6",
        action="store_true",
    )

    args = parser.parse_args(namespace=Arguments())

    db.ensure_db_existence()

    if not args.ignore_ipv4:
        scraper.my_ipv4 = get_server_ip("4")
    if not args.ignore_ipv6:
        scraper.my_ipv6 = get_server_ip("6")

    http_server = cast(HTTPServer, HTTPServer(WSGIContainer(app)))

    update_status = Thread(target=trackon.update_outdated_trackers)
    update_status.daemon = True
    update_status.start()

    warning_worker = Thread(target=trackon.warn_of_ip_conflicts_periodically)
    warning_worker.daemon = True
    warning_worker.start()

    submission_worker = Thread(target=ingest.submission_worker)
    submission_worker.daemon = True
    submission_worker.start()

    get_trackerlist_project_list = Thread(target=trackerlist_project.main)
    get_trackerlist_project_list.daemon = True
    get_trackerlist_project_list.start()

    http_server.listen(args.port, args.address)
    IOLoop.instance().start()
