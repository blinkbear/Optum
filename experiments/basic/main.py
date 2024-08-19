from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level
import logging
from scheduler import logger

logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.DEBUG)
set_config_file("experiments/basic/configs.yaml")
set_log_level("info")

manager.run()
