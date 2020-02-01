from newTrackon.views import app
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer


http_server = HTTPServer(WSGIContainer(app))

if __name__ == "__main__":
    http_server.listen(8080, address="127.0.0.1")
    IOLoop.instance().start()
