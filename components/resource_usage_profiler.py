from utils import get_all_pod_cpu_usage, get_pod_mem_usage
from utils.k8s import client as k8s_client
from models import EROTable
from custom_types import MemInMB
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

    def _get_all_pod_cpu_quota(self, node: str):
        return k8s_client.get_all_pod_cpu_quota(node)

    def get_node_ero(self, node: str) -> EROTable:
        pods_usage = get_all_pod_cpu_usage(node)
        pods_quota = self._get_all_pod_cpu_quota(node)
        pods_usage: dict[str, dict[str, float | str]] = {
            x: {"app": pods_quota[x]["app"], "cpu_usage": pods_usage[x]}
            for x in pods_usage
            if x in pods_quota
        }

        pod_names = list(pods_usage.keys())
        ero = EROTable()
        for i, pod_name_a in enumerate(pod_names):
            app_a = pods_usage[pod_name_a]["app"]
            for j in range(i, len(pod_names)):
                pod_name_b = pod_names[j]
                app_b = pods_usage[pod_name_b]["app"]
                if app_a == app_b:
                    continue
                # Equation (4)
                ro = (
                    pods_usage[pod_name_a]["cpu_usage"]
                    + pods_usage[pod_name_b]["cpu_usage"]
                ) / (
                    pods_quota[pod_name_a]["cpu_quota"]
                    + pods_quota[pod_name_b]["cpu_quota"]
                )
                key = [app_a, app_b]
                # Equation (5)
                ero[key] = max(ero.get(key, 0), ro)
        return ero

    def update_ero(self, nodes: list[str]) -> EROTable:
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

    def _build_mem_data(self) -> dict[str, MemInMB]:
        self.mem_data: dict[str, MemInMB] = {}
        if not os.path.exists(self.mem_data_path):
            return
        mem_csv = pd.read_csv(self.mem_data_path)
        for app, grp in mem_csv.groupby("app"):
            self.mem_data[app] = grp["mem"].quantile(0.95)

    def update_mem(self) -> dict[str, MemInMB]:
        mem_list: list[dict[str, MemInMB]] = []
        for pod in get_pod_mem_usage():
            app = k8s_client.get_pod_app_by_name(pod.name, pod.namespace)
            mem_list.append({"app": app, "mem": pod.mem})
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
        return self.mem_data.get(app, "100")
