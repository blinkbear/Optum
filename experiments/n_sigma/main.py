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

from ..data import DATA_ROOT

manager.data.set("hardware_data", f"{DATA_ROOT}/hardware_data.csv")
manager.data.set("node_data", f"{DATA_ROOT}/node_data.csv")

set_config_file("experiments/n_sigma/configs.yaml")
set_log_level("info")

manager.run()
