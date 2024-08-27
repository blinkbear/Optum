import logging

logging.basicConfig(
    level=logging.INFO,
    filename="log/n_sigma.log",
    filemode="a",
    format="<%(asctime)s>[%(name)s](%(levelname)s) %(message)s",
)

from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level

set_config_file("experiments/n_sigma/configs.yaml")
set_log_level("info")

manager.run()
