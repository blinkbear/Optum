from sklearn.ensemble import RandomForestRegressor
from ..models.types import *
from typing import Iterable
import numpy as np


def smape(y_true, y_pred):
    return 100 * np.mean(
        2 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred))
    )


class PSIModel:
    def train(
        self,
        x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil, QPS]],
        y: Iterable[PSI],
    ) -> AccyScore:
        self.model = RandomForestRegressor(max_depth=5)
        self.model.fit(x, y)
        pred_y = self.model.predict(x)
        for i in range(len(y)):
            if y[i] == 0 and pred_y[i] == 0:
                y[i] = 1
                pred_y[i] = 1
        score = smape(y, pred_y)
        print(score)
        return score

    def predict(
        self, x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil, QPS]]
    ) -> Iterable[PSI]:
        return self.model.predict(x)
