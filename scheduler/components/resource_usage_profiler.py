from models import EROTable, Node
from models.types import *
import pandas as pd
import os


class ResourceUsageProfiler:
    def __init__(self, ero_table_path: str, mem_data_path: str) -> None:
        self.ero_table = EROTable()
        self.ero_table_path = ero_table_path
        self.mem_data_path = mem_data_path
        self._build_mem_data()
        if os.path.exists(ero_table_path):
            with open(ero_table_path, "r") as file:
                for line in file.readlines():
                    key = line.split(":")[0].split(",")
                    value = line.split(":")[1]
                    self.ero_table[key] = float(value)

    def get_node_ero(self, node: Node) -> EROTable:
        ero = EROTable()
        pod_names = list(node.pods.keys())
        for i, pod_name_a in enumerate(pod_names[:-1]):
            pod_a = node.pods[pod_name_a]
            for pod_name_b in pod_names[i + 1 :]:
                pod_b = node.pods[pod_name_b]
                if pod_a.app_name == pod_b.app_name:
                    continue
                # Equation (4)
                ro = (pod_a.cpu_usage + pod_b.cpu_usage) / (
                    pod_a.cpu_requests + pod_b.cpu_requests
                )
                key = [pod_a.app_name, pod_b.app_name]
                # Equation (5)
                ero[key] = max(ero.get(key, 0), ro)
        return ero

    def update_ero(self, nodes: list[Node]) -> EROTable:
        for node in nodes:
            ero = self.get_node_ero(node)
            for key in ero:
                # Equation (5)
                self.ero_table[key] = max(self.ero_table.get(key, 0), ero[key])
        self.save_ero()
        return self.ero_table

    def save_ero(self):
        with open(self.ero_table_path, "w") as file:
            lines = []
            for key in self.ero_table:
                lines.append(f"{','.join(key)}:{self.ero_table[key]}\n")
            file.writelines(lines)

    def _build_mem_data(self) -> dict[AppName, MemInMB]:
        self.mem_data: dict[str, MemInMB] = {}
        if not os.path.exists(self.mem_data_path):
            return
        mem_csv = pd.read_csv(self.mem_data_path)
        for app, grp in mem_csv.groupby("app"):
            self.mem_data[app] = grp["mem"].quantile(0.95)

    def update_mem(self, nodes: list[Node]) -> dict[AppName, MemInMB]:
        mem_list = []
        # In Paper it says "Max mem utilization of App × mem requests of Pod"
        # Since in experiment we keep pods in same size of pod for an App
        # I simply use P95 of mem usage of all pods of that App
        for node in nodes:
            for pod in node.pods.values():
                mem_list.append({"app": pod.app_name, "mem": pod.mem_usage})
        mem_csv = pd.DataFrame(mem_list)
        if not os.path.exists(self.mem_data_path):
            open(self.mem_data_path, "w").close()
        is_empty = os.path.getsize(self.mem_data_path) == 0
        mem_csv.to_csv(self.mem_data_path, index=False, mode="a", header=is_empty)
        mem_csv = pd.read_csv(self.mem_data_path)
        self._build_mem_data()
        return self.mem_data

    def get_ero(self, app_1: str, app_2: str) -> float:
        return self.ero_table.get([app_1, app_2], 1.0)

    def get_em(self, app: str) -> MemInMB:
        # 100MiB is default pod size in this experiment
        return self.mem_data.get(app, 100)
