from dataclasses import dataclass

AppName = str
PodName = str
NodeName = str
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
NodeScore = float


@dataclass
class PodUtil:
    mem_util: Utilization
    cpu_util: Utilization


@dataclass
class OptumPredData:
    pod: str
    app: str
    job_type: str
    pred_performance_metric: float
    pred_node_cpu: float
    pred_node_mem: float
