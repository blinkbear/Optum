from utils.k8s import client as k8s_client
from utils.prom import client as prom_client
import logging
from models.types import *
from models import Node
from .app import App, default_app


class Cluster:
    def __init__(self, node_names: list[str], app_names: list[str]) -> None:
        self.node_names = node_names
        self.app_names = app_names

    def get_app(self, app_name: str) -> App:
        return self.apps.get(app_name, default_app)

    def get_node(self, node_name: str) -> Node:
        return self.nodes[node_name]

    def update(self, online_qps: QPS):
        self.nodes = k8s_client.get_all_nodes()
        self.apps: dict[AppName, App] = {}
        for name in self.node_names:
            if name not in self.node_names:
                logging.warn(f"Cluster:Failed to fetch info of node {name}.")
        pods = k8s_client.get_all_pods()
        pod_mem_usages = prom_client.fetch_pod_mem_usage()
        pod_cpu_usages = prom_client.fetch_pod_cpu_usage()
        for pod in pods.values():
            if pod.node_name not in self.nodes:
                continue
            pod.mem_usage = pod_mem_usages.get(pod.name, 0)
            pod.cpu_usage = pod_cpu_usages.get(pod.name, 0)
            self.nodes[pod.node_name].pods[pod.name] = pod
            app = self.apps.get(pod.app_name, App(pod.app_name, online_qps))
            self.apps[pod.app_name] = app
            app.pods.append(pod)
