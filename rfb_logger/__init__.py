import logging
import os
from ..rman_utils import prefs_utils

LOGGING_DISABLED = 100
CRITICAL = logging.CRITICAL
ERROR    = logging.ERROR
WARNING  = logging.WARNING
INFO     = logging.INFO
VERBOSE  = 15
DEBUG    = logging.DEBUG
NOTSET   = logging.NOTSET

__LOG_LEVELS__ = { 'CRITICAL': logging.CRITICAL,
               'ERROR': logging.ERROR,
               'WARNING': WARNING,
               'INFO': logging.INFO,
               'VERBOSE': 15,
               'DEBUG': logging.DEBUG,
               'NOTSET':  logging.NOTSET}

# logger format
LOG_FMT = '[%(levelname)s] (%(threadName)-10s) %(name)s %(funcName)s: %(message)s'

def set_logger_level(level):
    """
    Set the logging level for this module. This is only useful if the module
    is not using another logger.
    """
    __log__.setLevel(level)

def logger_level():
    """Return the logger's current level"""
    return __log__.level

def set_logger(logger):
    """
    Make this module adopt another logger and coalesce outputs into one stream.
    """
    global __log__
    __log__ = logger

def init_log_level():
    global __LOG_LEVELS__

    if 'RFB_LOG_LEVEL' in os.environ:
        level = os.environ['RFB_LOG_LEVEL']
        set_logger_level(__LOG_LEVELS__[level])
    else:
        rman_prefs = prefs_utils.get_addon_prefs()
        if rman_prefs and rman_prefs.rman_logging_level in __LOG_LEVELS__:
            level = __LOG_LEVELS__[rman_logging_level]
            set_logger_level(level)
        else:
            set_logger_level(WARNING)

    __log__.debug('logger initialized')
    __log__.debug('   |_ logger: %d', logger_level())

def rfb_log():
    """
    Return the logger.
    """
    return __log__


def get_logger(name):
    """
    Create a new configured logger and returns it.
    """
    log = logging.getLogger(name)
    # we don't set the logger's level to inherit from the parent logger.
    if log.handlers:
        return log
    fmt = logging.Formatter(LOG_FMT)
    shdlr = logging.StreamHandler()
    shdlr.setFormatter(fmt)
    log.addHandler(shdlr)
    log.propagate = False
    return log

__log__ = get_logger(__name__)
init_log_level()