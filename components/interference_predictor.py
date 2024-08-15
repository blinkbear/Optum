from .interference_profiler import InterferenceProfiler
from models.types import *

ModelName = str
ModelPath = str


class InterferencePredictor:
    def __init__(
        self,
        ls_model_data: dict[ModelName, ModelPath],
        be_model_data: dict[ModelName, ModelPath],
    ) -> None:
        self.profiler = InterferenceProfiler(ls_model_data, be_model_data)

    def get_ri_psi(
        self,
        app: AppName,
        pod_cpu_util: Utilization,
        pod_mem_util: Utilization,
        node_cpu_util: Utilization,
        node_mem_util: Utilization,
        qps: QPS,
    ) -> PSI:
        # Equation (9)
        return self.profiler.ls_profile(
            app, node_cpu_util, node_mem_util, pod_cpu_util, pod_mem_util, qps
        )

    def get_ri_ct(
        self,
        app: AppName,
        pod_cpu_util: Utilization,
        pod_mem_util: Utilization,
        node_cpu_util: Utilization,
        node_mem_util: Utilization,
    ) -> CT:
        # Equation (10)
        return self.profiler.be_profiler(
            app, node_cpu_util, node_mem_util, pod_cpu_util, pod_mem_util
        )
