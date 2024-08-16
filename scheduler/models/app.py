from ..models.types import *
from ..models import Pod
from scipy.optimize import curve_fit
from typing import Literal
import pandas as pd


def util_linear(x, a, b):
    return a * x + b


class App:
    def __init__(
        self, name: str, app_type: Literal["be", "ls"], data: dict[QPS, PodUtil]
    ) -> None:
        self.name = name
        self.qps: float = 0.0
        self.pods: list[Pod] = []
        self.data = data
        self.app_type = app_type

        if app_type == "be":
            return
        x, cpu_y, mem_y = [], [], []
        for qps, util in self.data.items():
            x.append(qps)
            cpu_y.append(util.cpu_util)
            mem_y.append(util.mem_util)
        self.pred_cpu, _ = curve_fit(util_linear, x, cpu_y)
        self.pred_mem, _ = curve_fit(util_linear, x, mem_y)

    def get_p95_pod_cpu_util(self) -> Utilization:
        if self.app_type == "be":
            return self.data[0.0].cpu_util
        if self.qps in self.data:
            return self.data[self.qps].cpu_util
        return util_linear(self.qps, *self.pred_cpu)

    def get_p95_pod_mem_util(self) -> Utilization:
        if self.app_type == "be":
            return self.data[0.0].mem_util
        if self.qps in self.data:
            return self.data[self.qps].mem_util
        return util_linear(self.qps, *self.pred_mem)

    def get_pod_counts(self) -> int:
        return len(self.pods) or 1

    def set_qps(self, qps: float) -> None:
        self.qps = qps


class NanApp(App):
    def __init__(self) -> None:
        self.pods: list[Pod] = []
        self.name = "nan"

    def get_p95_pod_cpu_util(self) -> Utilization:
        return pd.Series(
            [
                pod.cpu_usage / pod.cpu_requests
                for pod in self.pods
                if pod.cpu_requests is not None
            ]
        ).quantile(0.95)

    def get_p95_pod_mem_util(self) -> Utilization:
        return pd.Series(
            [
                pod.mem_usage / pod.mem_requests
                for pod in self.pods
                if pod.mem_requests is not None
            ]
        ).quantile(0.95)


def create_apps_from_data(data_path: str) -> dict[AppName, App]:
    # data_path -> hardware_data.csv from AEFM
    data = pd.read_csv(data_path)
    be_data = data.loc[data["microservice"].str.contains("pythonpi")]
    ls_data = data.loc[~data["microservice"].str.contains("pythonpi")]

    ls_data = (
        ls_data.groupby(["microservice", "round", "throughput"])[
            ["cpu_usage", "mem_usage"]
        ]
        .quantile(0.95)
        .reset_index()
        .groupby(["microservice", "throughput"])[["cpu_usage", "mem_usage"]]
        .mean()
        .reset_index()
    )
    be_data = be_data.assign(microservice="pythonpi")

    results = {}
    for app_name, app_data in ls_data.groupby("microservice"):
        app_data = app_data.apply(
            lambda x: (x["throughput"], PodUtil(x["mem_usage"], x["cpu_usage"])), axis=1
        )
        app_data = {float(x[0]): x[1] for x in app_data}
        results[app_name] = App(app_name, "ls", app_data)
    for app_name, app_data in be_data.groupby("microservice"):
        cpu_util = app_data["cpu_usage"].quantile(0.95)
        mem_util = app_data["mem_usage"].quantile(0.95)
        app_data = {0.0: PodUtil(mem_util, cpu_util)}
        results[app_name] = App(app_name, "be", app_data)

    return results


nan_app = NanApp()
