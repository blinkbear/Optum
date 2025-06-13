from scheduler.components.interference_profiler import InterferenceProfiler

ROOT = "data/profiling_sn"
MODEL_PATH = "data/models/um_profiling"
# InterferenceProfiler.train_be(
#     f"{ROOT}/hardware_data.csv",
#     f"{ROOT}/node_data.csv",
#     f"{ROOT}/jct_data.csv",
#     MODEL_PATH,
# )

InterferenceProfiler.train_ls(
    f"{ROOT}/pod_data.csv",
    f"{ROOT}/node_data.csv",
    f"{ROOT}/assignment_data.csv",
    MODEL_PATH,
)
