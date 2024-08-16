from scheduler.components.scheduler import (
    Scheduler,
    InterferencePredictor,
    ResourceUsagePredictor,
)
from scheduler.models import Pod, Cluster
from scheduler.models.app import create_apps_from_data
from scheduler.utils import logger
import logging

logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.DEBUG)

ls_models = {
    "frontend": "data/models/frontend.ls",
    "geo": "data/models/geo.ls",
    "profile": "data/models/profile.ls",
    "rate": "data/models/rate.ls",
    "reservation": "data/models/reservation.ls",
    "search": "data/models/search.ls",
}
be_models = {"pythonpi": "data/models/pythonpi.be"}
inf_pred = InterferencePredictor(ls_models, be_models)
res_pred = ResourceUsagePredictor("data/ero_table", "data/mem_table")

apps = create_apps_from_data("data/understanding_11/hardware_data.csv")
cluster = Cluster(["k8s-bk-3", "k8s-bk-6", "k8s-bk-8", "k8s-bk-x"], apps)
scheduler = Scheduler(cluster, inf_pred, res_pred)
scheduler.schedule([Pod("test", "frontend", cpu_requests=1, mem_requests=1024)], 100)[
    "test"
].name

# from scheduler.components.interference_profiler import InterferenceProfiler

# InterferenceProfiler.train_ls(
#     "data/understanding_11/hardware_data.csv",
#     "data/understanding_11/node_data.csv",
#     "data/models",
# )

# InterferenceProfiler.train_be(
#     "data/understanding_11/hardware_data.csv",
#     "data/understanding_11/node_data.csv",
#     "data/understanding_11/jct_data.csv",
#     "data/models",
# )
