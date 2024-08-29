import logging

logging.basicConfig(
    level=logging.INFO,
    filename="log/resource_central.log",
    filemode="a",
    format="<%(asctime)s>[%(name)s](%(levelname)s) %(message)s",
)

from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level

from ..data import DATA_ROOT

manager.data.set("hardware_data", f"{DATA_ROOT}/hardware_data.csv")

set_config_file("experiments/resource_central/configs.yaml")
set_log_level("info")

manager.run()
