from typing import Literal
from ..models.types import *


class Pod:
    def __init__(
        self,
        name: str,
        app: str,
        node_name: str | None = None,
        namespace: str | None = None,
        type: Literal["be", "ls"] | None = None,
        cpu_requests: CPUCores | None = None,
        cpu_usage: CPUCores | None = None,
        mem_requests: MemInMB | None = None,
        mem_usage: MemInMB | None = None,
    ) -> None:
        self.name = name
        self.node_name = node_name
        self.type = type
        self.app_name = app
        self.cpu_requests = cpu_requests
        self.cpu_usage = cpu_usage
        self.mem_requests = mem_requests
        self.mem_usage = mem_usage
        self.namespace = namespace
