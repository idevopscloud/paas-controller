import os
import logging
from logging.handlers import RotatingFileHandler
from settings import settings

LOG = None

def get_logger():
    logging.basicConfig(format = '[%(levelname)s] [%(asctime)s] %(message)s', 
                        level = logging.INFO) 
    handlers = [
        RotatingFileHandler(settings.LOG_PATH,
                            mode='a',
                            maxBytes = settings.MAX_LOG_SIZE * 1024 * 1024,
                            backupCount = settings.MAX_LOG_COUNT),
    ]
    fmt = logging.Formatter('[%(levelname)s] [%(asctime)s] %(message)s')
    logger = logging.getLogger()
    for handler in handlers:
        handler.setFormatter(fmt)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger

if not os.path.exists(os.path.dirname(settings.LOG_PATH)):
    os.makedirs(os.path.dirname(settings.LOG_PATH))
LOG = get_logger()

