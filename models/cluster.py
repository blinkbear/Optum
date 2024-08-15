from utils.k8s import client as k8s_client
import logging
from custom_types import AppName
from .app import App


class Cluster:
    def __init__(self, node_names: list[str], app_names: list[str]) -> None:
        self.node_names = node_names
        self.app_names = app_names

    def update_apps(self):
        self.apps: dict[AppName, App]
    
    def update(self):
        self.update_nodes()
        self.update_apps()

    def update_nodes(self):
        self.nodes = k8s_client.get_all_nodes()
        for name in self.node_names:
            if name not in self.node_names:
                logging.warn(f"Cluster:Failed to fetch info of node {name}.")
        pods = k8s_client.get_all_pods()
        for pod in pods.values():
            self.nodes[pod.node_name].pods[pod.name] = pod
        
