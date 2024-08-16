from ..models.types import *
from .pod import Pod


class Node:
    def __init__(self, name: str, ip: str, cpu_cap: CPUCores, mem_cap: MemInMB) -> None:
        self.name = name
        self.ip = ip
        self.cpu_cap = cpu_cap
        self.mem_cap = mem_cap
        self.pods: dict[PodName, Pod] = {}
