from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level
import logging

logging.basicConfig(level=logging.INFO)
set_config_file("experiments/basic/configs.yaml")
set_log_level("info")

manager.run()
