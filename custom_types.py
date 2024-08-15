PodName = str
MemInMB = float
CPUCores = float
UsedCores = float
# Utilization range: 0 - 1
Utilization = float
# PSI range: 0 - 1
PSI = float
# Completion time is also normalized to: 0 - 1
CT = float
AccyScore = float
QPS = float
HostCPUUtil = Utilization
HostMemUtil = Utilization
PodCPUUtil = Utilization
PodMemUtil = Utilization


class Pod:
    def __init__(
        self,
        name: str,
        app: str,
        node: str | None = None,
        type: str | None = None,
        cpu_requests: CPUCores | None = None,
    ) -> None:
        self.name = name
        self.node = node
        self.type = type
        self.app = app
        self.cpu_requests = cpu_requests
