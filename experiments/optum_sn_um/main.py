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

set_config_file("experiments/optum_sn_um/configs.yaml")
set_log_level("info")

from ..data import MODEL_ROOT, DATA_ROOT

# manager.data.set(
#     "ls_models",
#     {
#         "co": f"{MODEL_ROOT}/frontend.ls",
#         "geo": f"{MODEL_ROOT}/geo.ls",
#         "profile": f"{MODEL_ROOT}/profile.ls",
#         "rate": f"{MODEL_ROOT}/rate.ls",
#         "reservation": f"{MODEL_ROOT}/reservation.ls",
#         "search": f"{MODEL_ROOT}/search.ls",
#     },
# )
manager.data.set(
    "ls_models",
    {
        "compose-post-service": f"{MODEL_ROOT}/compose-post-service.ls",
        "frontend": f"{MODEL_ROOT}/frontend.ls",
        "geo": f"{MODEL_ROOT}/geo.ls",
        "media-service": f"{MODEL_ROOT}/media-service.ls",
        "post-storage-service": f"{MODEL_ROOT}/post-storage-service.ls",
        "profile": f"{MODEL_ROOT}/profile.ls",
        "rate": f"{MODEL_ROOT}/rate.ls",
        "reservation": f"{MODEL_ROOT}/reservation.ls",
        "search": f"{MODEL_ROOT}/search.ls",
        "social-graph-service": f"{MODEL_ROOT}/social-graph-service.ls",
        "text-service": f"{MODEL_ROOT}/text-service.ls",
        "unique-id-service": f"{MODEL_ROOT}/unique-id-service.ls",
        "url-shorten-service": f"{MODEL_ROOT}/url-shorten-service.ls",
        "user-mention-service": f"{MODEL_ROOT}/user-mention-service.ls",
        "user-service": f"{MODEL_ROOT}/user-service.ls",
        "user-timeline-service": f"{MODEL_ROOT}/user-timeline-service.ls",
        "write-home-timeline-service": f"{MODEL_ROOT}/write-home-timeline-service.ls",
    },
)


manager.data.set("be_models", {"pythonpi": f"{MODEL_ROOT}/pythonpi.be"})
manager.data.set("hardware_data", f"{DATA_ROOT}/hardware_data.csv")

manager.run()
