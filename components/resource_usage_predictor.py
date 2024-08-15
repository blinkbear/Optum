from .resource_usage_profiler import ResourceUsageProfiler
from models.types import *
from models import Pod
from itertools import zip_longest


class ResourceUsagePredictor:
    def __init__(self, ero_table_path: str, mem_data_path: str) -> None:
        self.profiler = ResourceUsageProfiler(ero_table_path, mem_data_path)

    def get_ec(self, pod_1: Pod, pod_2: Pod) -> CPUCores:
        ero = self.profiler.get_ero(pod_1.app, pod_2.app)
        # Equation (7)
        return ero * (pod_1.cpu_requests + pod_2.cpu_requests)

    def get_em(self, pod_1: Pod) -> MemInMB:
        return self.profiler.get_em(pod_1.app)

    def get_poc(self, pods: list[Pod]) -> CPUCores:
        # Equation (8)
        poc = 0
        for pod_1, pod_2 in zip_longest(pods[0::2], pods[1::2]):
            if pod_2 is None:
                poc += pod_1.cpu_requests
            else:
                poc += self.get_ec(pod_1, pod_2)
        return poc

    def get_pom(self, pods: list[Pod]) -> MemInMB:
        return sum([self.get_em(pod) for pod in pods])
