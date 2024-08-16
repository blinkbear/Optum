from models.types import *
from typing import TypeVar, Literal
import pickle
from kubernetes.client.models.v1_pod import V1Pod

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


def get_pod_type(k8s_pod: V1Pod) -> Literal["be", "ls"]:
    return (
        "be"
        if k8s_pod.metadata.namespace not in ["hotel-reserv", "social-network"]
        else "ls"
    )
