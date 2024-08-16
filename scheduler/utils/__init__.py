from ..models.types import *
from ..models import App
from typing import TypeVar
import pickle
import pandas as pd

T = TypeVar("T")


def load_obj(path: str, obj_class: T) -> T:
    with open(path, "rb") as file:
        obj: obj_class = pickle.load(file)
        return obj


def save_obj(path: str, obj) -> None:
    with open(path, "wb") as file:
        pickle.dump(obj, file)


def parse_cpu_unit(k8s_cpu_str: str) -> CPUCores:
    if k8s_cpu_str.endswith("m"):
        return float(k8s_cpu_str[:-1]) / 1000
    return float(k8s_cpu_str)



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
