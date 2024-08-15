from models.types import *
from models import Pod
import pandas as pd


class App:
    def __init__(self, name: str, qps: float) -> None:
        self.name = name
        self.qps = qps
        self.pods: list[Pod] = []

    def get_p95_pod_cpu_util(self) -> Utilization:
        return pd.Series(
            [pod.cpu_usage / pod.cpu_requests for pod in self.pods]
        ).quantile(0.95)

    def get_p95_pod_mem_util(self) -> Utilization:
        return pd.Series(
            [
                pod.mem_usage / pod.mem_requests
                for pod in self.pods
                if pod.mem_requests is not None
            ]
        ).quantile(0.95)

    def get_pod_counts(self) -> int:
        return len(self.pods) or 1


default_app = App("default", 0)
