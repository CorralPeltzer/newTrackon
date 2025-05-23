import argparse
from newTrackon.views import app
from newTrackon.scraper import get_server_ip
from newTrackon import trackerlist_project, trackon, scraper, db
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from threading import Thread


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", type=str, help="Address for the flask server", default="localhost")
    parser.add_argument("--port", type=int, help="Port for the flask server", default=8080)
    parser.add_argument(
        "--ignore-ipv4",
        help="Ignore newTrackon server IPv4 detection",
        dest="ignore_ipv4",
        action="store_true",
    )
    parser.add_argument(
        "--ignore-ipv6",
        help="Ignore newTrackon server IPv6 detection",
        dest="ignore_ipv6",
        action="store_true",
    )

    args = parser.parse_args()

    db.ensure_db_existence()

    if not args.ignore_ipv4:
        scraper.my_ipv4 = get_server_ip("4")
    if not args.ignore_ipv6:
        scraper.my_ipv6 = get_server_ip("6")

    http_server = HTTPServer(WSGIContainer(app))

    update_status = Thread(target=trackon.update_outdated_trackers)
    update_status.daemon = True
    update_status.start()

    get_trackerlist_project_list = Thread(target=trackerlist_project.main)
    get_trackerlist_project_list.daemon = True
    get_trackerlist_project_list.start()

    http_server.listen(args.port, args.address)
    IOLoop.instance().start()
