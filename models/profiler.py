from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from custom_types import AccyScore, Utilization, QPS, PSI, JCT
from typing import Iterable
from utils import get_all_pod_cpu_usage
from utils.k8s import client as k8s_client

HostCPUUtil = Utilization
HostMemUtil = Utilization
PodCPUUtil = Utilization
PodMemUtil = Utilization


class LSInterferenceProfiler:
    def train(
        self,
        x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil, QPS]],
        y: Iterable[PSI],
    ) -> AccyScore:
        self.model = RandomForestClassifier(max_depth=5)
        self.model.fit(x, y)
        pred_y = self.model.predict(x)
        return accuracy_score(pred_y, y)

    def predict(
        self, x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil, QPS]]
    ) -> Iterable[PSI]:
        return self.model.predict(x)


class BEInterferenceProiler:
    def train(
        self,
        x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil]],
        y: Iterable[JCT],
    ) -> AccyScore:
        """Train BE interference profiler

        Args:
            x (Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil]]): All utilization should be **MAX** utilization.
            y (Iterable[JCT]): Job completion time.

        Returns:
            AccyScore: Accuracy score gained by `accuracy_score` function
        """
        self.model = RandomForestClassifier(max_depth=5)
        self.model.fit(x, y)
        pred_y = self.model.predict(x)
        return accuracy_score(pred_y, y)

    def predict(
        self, x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil]]
    ) -> Iterable[JCT]:
        return self.model.predict(x)


class EROTable(dict):
    def __setitem__(self, key: list, value: float) -> None:
        return super().__setitem__(tuple(sorted(key)), value)

    def __getitem__(self, key: list) -> float:
        return super().__getitem__(tuple(sorted(key)))

    def get(self, key: list, default) -> float:
        return super().get(tuple(sorted(key)), default)


class ResourceUsageProfiler:
    def _get_all_pod_cpu_quota(self, node: str):
        return k8s_client.get_all_pod_cpu_quota(node)

    def get_node_ero(self, node: str) -> EROTable:
        pods_usage = get_all_pod_cpu_usage(node)
        pods_quota = self._get_all_pod_cpu_quota(node)
        pods_usage: dict[str, dict[str, float | str]] = {
            x: {"app": pods_quota[x]["app"], "cpu_usage": pods_usage[x]}
            for x in pods_usage
            if x in pods_quota
        }

        pod_names = list(pods_usage.keys())
        ero = EROTable()
        for i, pod_name_a in enumerate(pod_names):
            app_a = pods_usage[pod_name_a]["app"]
            for j in range(i, len(pod_names)):
                pod_name_b = pod_names[j]
                app_b = pods_usage[pod_name_b]["app"]
                if app_a == app_b:
                    continue
                ro = (
                    pods_usage[pod_name_a]["cpu_usage"]
                    + pods_usage[pod_name_b]["cpu_usage"]
                ) / (
                    pods_quota[pod_name_a]["cpu_quota"]
                    + pods_quota[pod_name_b]["cpu_quota"]
                )
                key = [app_a, app_b]
                ero[key] = max(ero.get(key, 0), ro)
        return ero

    def get_ero(self, nodes: list[str]) -> EROTable:
        results = EROTable()
        for node in nodes:
            ero = self.get_node_ero(node)
            for key in ero:
                results[key] = max(results.get(key, 0), ero[key])
        return results
