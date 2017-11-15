#!/usr/bin/env python
# Organization : VLEAD, Virtual-Labs
# Services exposed by LoggingServer
# http://host-name/log/

import threading

# tornado imports
import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpserver
from tornado.options import define, options

from __init__ import *
from utils.envsetup import EnvSetUp
import httplogging.helper as helper

define("port", default=8239, help="run on the given port", type=int)


class LogHandler(tornado.web.RequestHandler):
    def get(self):
        print "Hello World"

    def post(self):
        """Spawns a new thread for every request and passes the request as \
        arguments to log() function"""
        t = threading.Thread(target=helper.log,
                             args=(self.request.arguments,))
        t.start()

class TestHandler(tornado.web.RequestHandler):
    def get(self):
        if helper.qmsg.q_emp():
            self.write("nth")
        else:
            self.write(helper.qmsg.get_msg())

    def post(self):
        pass

class OtherHandler(tornado.web.RequestHandler):
    def get(self):
        pass

    def post(self):
        pass

if __name__ == "__main__":
    env = EnvSetUp.Instance()
    app = tornado.web.Application(
        handlers=[
            (r"/log/.*", LogHandler),
            (r"/test", TestHandler),
            (r"/.*", OtherHandler),
        ],
        debug=True)
    http_server = tornado.httpserver.HTTPServer(app)
    config_spec = env.get_config_spec()
    options.port = config_spec["LOGGING_CONFIGURATION"]["LOGSERVER_CONFIGURATION"]["SERVER_PORT"]
    http_server.bind(options.port)
    http_server.start(1)
    print "http logging service started"
    tornado.ioloop.IOLoop.instance().start()
