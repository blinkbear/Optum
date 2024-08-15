from models.types import *


class App:
    def __init__(self, name: str, qps: float) -> None:
        self.name = name
        self.qps = qps

    def get_p95_pod_cpu_util(self) -> Utilization:
        pass

    def get_p95_pod_mem_util(self) -> Utilization:
        pass

    def get_pod_counts(self) -> int:
        pass
