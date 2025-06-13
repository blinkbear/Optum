import logging

logging.basicConfig(
    level=logging.INFO,
    filename="log/psi_corr_pod_node_cpu_sn.log",
    filemode="a",
    format="<%(asctime)s>[%(name)s]%(levelname)s-%(message)s",
)

from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level

set_config_file("experiments/psi_corr_pod_node_cpu_sn/configs.yaml")
set_log_level("info")
manager.run()
