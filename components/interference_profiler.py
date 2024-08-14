from custom_types import *
from utils import load_obj
from models.profiler import LSProfiler, BEProiler

ModelName = str
ModelPath = str


class InterferenceProfiler:
    def __init__(
        self,
        ls_model_data: dict[ModelName, ModelPath],
        be_model_data: dict[ModelName, ModelPath],
    ) -> None:
        self.ls_models: dict[str, LSProfiler] = {}
        self.be_models: dict[str, BEProiler] = {}
        for name in ls_model_data:
            path = ls_model_data[name]
            self.ls_models[name] = load_obj(path, LSProfiler)
        for name in be_model_data:
            path = be_model_data[name]
            self.be_models[name] = load_obj(path, BEProiler)

    def ls_profile(
        self,
        app: str,
        node_cpu_util: Utilization,
        node_mem_util: Utilization,
        pod_cpu_util: Utilization,
        pod_mem_util: Utilization,
        qps: QPS,
    ) -> PSI:
        if node_cpu_util >= 1:
            return 1.0
        if app not in self.ls_models:
            return 1.0
        model = self.ls_models[app]
        x = [(node_cpu_util, node_mem_util, pod_cpu_util, pod_mem_util, qps)]
        result = model.predict(x)[0]
        return max(result, 0.0)

    def be_profiler(
        self,
        app: str,
        node_cpu_util: Utilization,
        node_mem_util: Utilization,
        pod_cpu_util: Utilization,
        pod_mem_util: Utilization,
    ) -> JCT:
        if node_cpu_util > 1:
            return 1.0
        if app not in self.be_models:
            return 1.0
        model = self.be_models[app]
        x = [(node_cpu_util, node_mem_util, pod_cpu_util, pod_mem_util)]
        result = model.predict(x)[0]
        return max(result, 0.0)
