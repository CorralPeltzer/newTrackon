import argparse
import subprocess
from newTrackon.views import app
from newTrackon.scraper import get_server_ip
from newTrackon import trackerlist_project, trackon, utils
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from threading import Thread


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='newTrackon arguments')
    parser.add_argument('--ignore-ipv4', help='Ignore newTrackon server IPv4 detection', dest='ignore_ipv4', action='store_true')
    parser.add_argument('--ignore-ipv6', help='Ignore newTrackon server IPv6 detection', dest='ignore_ipv6', action='store_true')

    args = parser.parse_args()
    if not args.ignore_ipv4:
        utils.my_ipv4 = get_server_ip('4')
    if not args.ignore_ipv6:
        utils.my_ipv6 = get_server_ip('6')

    http_server = HTTPServer(WSGIContainer(app))

    update_status = Thread(target=trackon.update_outdated_trackers)
    update_status.daemon = True
    update_status.start()

    get_trackerlist_project_list = Thread(target=trackerlist_project.main)
    get_trackerlist_project_list.daemon = True
    get_trackerlist_project_list.start()

    http_server.listen(8080, address="127.0.0.1")
    IOLoop.instance().start()
