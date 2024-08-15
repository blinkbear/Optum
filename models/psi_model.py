from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from custom_types import *
from typing import Iterable


class PSIModel:
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
