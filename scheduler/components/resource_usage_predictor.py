from .resource_usage_profiler import ResourceUsageProfiler
from ..models.types import *
from ..models import Pod, Node
from itertools import zip_longest
from ..utils import logger


class ResourceUsagePredictor:
    def __init__(self, ero_table_path: str, mem_data_path: str) -> None:
        self.profiler = ResourceUsageProfiler(ero_table_path, mem_data_path)

    def get_em(self, pod_1: Pod) -> MemInMB:
        em = self.profiler.get_em(pod_1.app_name)
        logger.debug(f"ResourceUsagePredictor.get_em: EM of <{pod_1.name}> is {em}")
        return em

    def get_poc(self, pods: list[Pod]) -> CPUCores:
        # To avoid compute ec between two pods from the same app.
        # We firstly compute the cummulative CPU requests of all pods from each app.
        # Then apply ero between apps directly.
        apps = {}
        for pod in pods:
            apps[pod.app_name] = apps.get(pod.app_name, 0) + pod.cpu_requests
        # Equation (8)
        poc = 0
        app_names = list(apps.keys())
        for app_1, app_2 in zip_longest(app_names[0::2], app_names[1::2]):
            if app_2 is None:
                ec = apps[app_1]
                logger.debug(
                    f"ResourceUsagePredictor.get_poc: EC of {{{app_1}}} is {ec}"
                )
            else:
                ero = self.profiler.get_ero(app_1, app_2)
                ec = ero * (apps[app_1] + apps[app_2])
                logger.debug(
                    f"ResourceUsagePredictor.get_poc: EC of "
                    f"{{{app_1}}} and {{{app_2}}} is {ec}"
                )
            poc += ec
        return poc

    def get_pom(self, pods: list[Pod]) -> MemInMB:
        return sum([self.get_em(pod) for pod in pods])

    def update(self, nodes: list[Node]) -> None:
        self.profiler.update(nodes)
