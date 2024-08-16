from sklearn.ensemble import RandomForestRegressor
from models.types import *
from typing import Iterable


class CTModel:
    def train(
        self,
        x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil]],
        y: Iterable[CT],
    ) -> AccyScore:
        self.model = RandomForestRegressor(max_depth=5)
        self.model.fit(x, y)
        return self.model.score(x, y)

    def predict(
        self, x: Iterable[tuple[HostCPUUtil, HostMemUtil, PodCPUUtil, PodMemUtil]]
    ) -> Iterable[CT]:
        return self.model.predict(x)
