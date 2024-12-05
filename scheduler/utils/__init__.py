from ..models.types import *
from typing import TypeVar
import pickle
import logging

logger = logging.getLogger("Base")
logger.info("Greetings from Optum base!")
logger.info("We will use <> to represents pods")
logger.info("We will use [] to represents nodes")
logger.info("We will use {} to represents apps")

T = TypeVar("T")


def load_obj(path: str, obj_class: type[T]) -> T:
    with open(path, "rb") as file:
        obj: obj_class = pickle.load(file)
    if not isinstance(obj, obj_class):
        raise TypeError(f"Expected object of type {obj_class}, but got {type(obj)}")
    return obj


def save_obj(path: str, obj) -> None:
    with open(path, "wb") as file:
        pickle.dump(obj, file)


def parse_cpu_unit(k8s_cpu_str: str) -> CPUCores:
    if k8s_cpu_str.endswith("m"):
        return float(k8s_cpu_str[:-1]) / 1000
    return float(k8s_cpu_str)


def parse_mem_unit(k8s_mem_str: str) -> MemInMB:
    if k8s_mem_str.endswith("Ki"):
        return float(k8s_mem_str[:-2]) / 1024
    if k8s_mem_str.endswith("Mi"):
        return float(k8s_mem_str[:-2])
    if k8s_mem_str.endswith("Gi"):
        return float(k8s_mem_str[:-2]) * 1024
    pass
