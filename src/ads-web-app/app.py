from flask import Flask
from api import *
from config import LOG_FILE_DIRECTORY
from config import LOG_FILE
from config import LOG_LEVEL
from tornado import websocket, web, ioloop,httpserver,gen
from tornado.wsgi import WSGIContainer
from tornado.web import FallbackHandler, RequestHandler, Application
import os, json,requests

cl = []

def create_app():
    # init our app
    app = Flask(__name__)
    app.secret_key = 'development'
    # register blueprints
    app.register_blueprint(api)
    configure_logging(app)
    return app


def configure_logging(app):
    import logging
    import logging.handlers
    formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(filename)s:'
                                  ' %(funcName)s():%(lineno)d: %(message)s')

    # Also error can be sent out via email. So we can also have a SMTPHandler?
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           LOG_FILE_DIRECTORY)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = "%s/%s" % (log_dir, LOG_FILE)
    os.system("sudo touch %s" % log_file)
    os.system("sudo chmod 777 %s" % log_file)
    max_size = 1024 * 1024 * 20  # Max Size for a log file: 20MB
    log_handler = logging.handlers.RotatingFileHandler(log_file,
                                                       maxBytes=max_size,
                                                       backupCount=10)
    log_level = LOG_LEVEL
    log_handler.setFormatter(formatter)
    app.logger.addHandler(log_handler)
    app.logger.setLevel(log_level)

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl:
            cl.append(self)

    def on_close(self):
        if self in cl:
            cl.remove(self)


def send_msgs():
    hello={
        "value":"Ping"
    }
#    r = requests.get("http://localhost:7777/test")
    [client.write_message(hello) for client in cl]

#+NAME: run_server
if __name__ == "__main__":
    app = create_app()
    tr = WSGIContainer(app)
    run_app = Application(
        handlers = [
            (r"/ws", SocketHandler),
            (r".*", FallbackHandler, dict(fallback=tr)),
        ],
        debug=True)
    run = httpserver.HTTPServer(run_app)
    run.listen(8080)
    ioloop.PeriodicCallback(send_msgs, 1000).start()
    ioloop.IOLoop.instance().start()
