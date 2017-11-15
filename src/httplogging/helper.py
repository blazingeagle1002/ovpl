# logging imports
import logging
import logging.handlers

# other impors
import os
from __init__ import *
from utils.envsetup import EnvSetUp
from Queue import *

env = EnvSetUp.Instance()
used_loggers = {}
config_spec = env.get_config_spec()
FILE_PATH = config_spec["LOGGING_CONFIGURATION"]["LOGSERVER_CONFIGURATION"]["FILE_PATH"]

if not os.path.isdir(FILE_PATH):
    os.mkdir(FILE_PATH)


def get_logger(name):
    """Returns logger object"""
    logger = None
    if name in used_loggers:
        logger = used_loggers[name]
    else:
        logger = logging.getLogger(name)
        used_loggers[name] = logger
        LOG_FILE_PATH = FILE_PATH + str(name) + '.log'
        print LOG_FILE_PATH
        timed_handler = logging.handlers.TimedRotatingFileHandler(
            LOG_FILE_PATH, when='midnight', backupCount=5)
        formatter = logging.Formatter('%(asctime)s: %(message)s',
                                      datefmt='%m/%d/%Y %I:%M:%S %p')
        timed_handler.setFormatter(formatter)
        logger.addHandler(timed_handler)
        logger.propagate = False
        logger.has_handlers = True
    return logger


def log(arguments):
    """Creates an instance of a LogRecord object and \
    Handles the record by passing it to all handlers \
    associated with this logger"""

    levelname = arguments['levelname'][0]
    pathname = arguments['pathname'][0]
    lineno = arguments['lineno'][0]
    name = arguments['name'][0]
    message = arguments['msg'][0]
    qmsg.put_msg(message)
    funcName = arguments['funcName'][0]
    logger = get_logger(name)
    fmt_string = "%(levelname)s: %(pathname)s:%(lineno)-4s-> %(message)s"
    record_format_args = {
        'levelname': levelname,
        'pathname': pathname,
        'lineno': lineno,
        'message': message
    }
    record = logger.makeRecord(name, levelname, funcName, lineno,
                               fmt_string, record_format_args, None)
    logger.handle(record)

class Message():
    def __init__(self):
        self.msg = Queue()
    def get_msg(self):
        if not self.msg.empty():
            return self.msg.get()
    def put_msg(self,mesg):
        self.msg.put(mesg)
    def q_emp(self):
        return self.msg.empty()

qmsg = Message()
