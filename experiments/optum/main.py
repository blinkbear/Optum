import logging

logging.basicConfig(
    level=logging.INFO,
    filename="log/optum.log",
    filemode="a",
    format="<%(asctime)s>[%(name)s]%(levelname)s-%(message)s",
)

from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level

set_config_file("experiments/optum/configs.yaml")
set_log_level("info")

from ..data import MODEL_ROOT, DATA_ROOT

manager.data.set(
    "ls_models",
    {
        "frontend": f"{MODEL_ROOT}/frontend.ls",
        "geo": f"{MODEL_ROOT}/geo.ls",
        "profile": f"{MODEL_ROOT}/profile.ls",
        "rate": f"{MODEL_ROOT}/rate.ls",
        "reservation": f"{MODEL_ROOT}/reservation.ls",
        "search": f"{MODEL_ROOT}/search.ls",
    },
)
manager.data.set("be_models", {"pythonpi": f"{MODEL_ROOT}/pythonpi.be"})
manager.data.set("hardware_data", f"{DATA_ROOT}/hardware_data.csv")

manager.run()
