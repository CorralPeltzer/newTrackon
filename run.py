from newTrackon.views import app
from newTrackon import trackerlist_project, trackon
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from threading import Thread

http_server = HTTPServer(WSGIContainer(app))

update_status = Thread(target=trackon.update_outdated_trackers)
update_status.daemon = True
update_status.start()

get_trackerlist_project_list = Thread(target=trackerlist_project.main)
get_trackerlist_project_list.daemon = True
get_trackerlist_project_list.start()


if __name__ == "__main__":
    http_server.listen(8080, address="127.0.0.1")
    IOLoop.instance().start()
