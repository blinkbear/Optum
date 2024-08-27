from ..models.types import *
from .pod import Pod


class Node:
    def __init__(self, name: str, ip: str, cpu_cap: CPUCores, mem_cap: MemInMB) -> None:
        self.name = name
        self.ip = ip
        self.cpu_cap = cpu_cap
        self.mem_cap = mem_cap
        self.pods: dict[PodName, Pod] = {}

    def get_cpu_requested(self) -> CPUCores:
        cpu_requested = 0
        for pod in self.pods.values():
            cpu_requested += pod.cpu_requests
        return cpu_requested

    def get_mem_requested(self) -> MemInMB:
        mem_requested = 0
        for pod in self.pods.values():
            mem_requested += pod.mem_requests
        return mem_requested

    def get_cpu_usage(self) -> CPUCores:
        cpu_usage = 0
        for pod in self.pods.values():
            cpu_usage += pod.cpu_usage
        return cpu_usage

    def get_cpu_util(self) -> Utilization:
        return self.get_cpu_usage / self.cpu_cap

    def get_mem_usage(self) -> MemInMB:
        mem_usage = 0
        for pod in self.pods.values():
            mem_usage += pod.mem_usage
        return mem_usage

    def get_mem_util(self) -> Utilization:
        return self.get_mem_usage / self.mem_cap
