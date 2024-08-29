from scheduler.components.interference_profiler import InterferenceProfiler

ROOT = "data/experiment_02/profiling"
MODEL_PATH = "data/models/experiment_02"
InterferenceProfiler.train_be(
    f"{ROOT}/hardware_data.csv",
    f"{ROOT}/node_data.csv",
    f"{ROOT}/jct_data.csv",
    MODEL_PATH,
)

InterferenceProfiler.train_ls(
    f"{ROOT}/hardware_data.csv",
    f"{ROOT}/node_data.csv",
    f"{ROOT}/assignment.csv",
    MODEL_PATH,
)
