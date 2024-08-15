from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from custom_types import AccyScore, Utilization, QPS, PSI, CT
from typing import Iterable


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
        y: Iterable[CT],
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
    ) -> Iterable[CT]:
        return self.model.predict(x)


class EROTable(dict):
    def __setitem__(self, key: Iterable, value: float) -> None:
        return super().__setitem__(tuple(sorted(key)), value)

    def __getitem__(self, key: Iterable) -> float:
        return super().__getitem__(tuple(sorted(key)))

    def get(self, key: Iterable, default) -> float:
        return super().get(tuple(sorted(key)), default)
