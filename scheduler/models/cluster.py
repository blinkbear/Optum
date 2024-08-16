from ..utils.k8s import client as k8s_client
from ..utils.prom import client as prom_client
from ..utils import logger
from ..models.types import *
from ..models import Node, App
from .app import App, nan_app


class Cluster:
    def __init__(self, node_names: list[str], apps: dict[AppName, App]) -> None:
        self.node_names = node_names
        self.apps = apps

    def get_app(self, app_name: str) -> App:
        return self.apps.get(app_name, nan_app)

    def get_node(self, node_name: str) -> Node:
        return self.nodes[node_name]

    def update(self, online_qps: QPS):
        self.nodes: dict[NodeName, Node] = {}
        nodes = k8s_client.get_all_nodes()
        nan_app.pods.clear()
        for app in self.apps.values():
            app.pods.clear()
            app.set_qps(online_qps)
        for name in self.node_names:
            if name not in nodes:
                logger.warn(f"Cluster.update: Failed to fetch info of [{name}]")
                continue
            self.nodes[name] = nodes[name]
        logger.debug(
            f"Cluster.update: Cluster gets nodes [{','.join([x.name for x in self.nodes.values()])}]"
        )
        pods = k8s_client.get_all_pods()
        pod_mem_usages = prom_client.fetch_pod_mem_usage()
        pod_cpu_usages = prom_client.fetch_pod_cpu_usage()
        for pod in pods.values():
            if pod.node_name not in self.nodes:
                continue
            pod.mem_usage = pod_mem_usages.get(pod.name, 0)
            pod.cpu_usage = pod_cpu_usages.get(pod.name, 0)
            self.nodes[pod.node_name].pods[pod.name] = pod
            logger.debug(f"Cluster.update: Assign <{pod.name}> to [{pod.node_name}]")
            app = self.get_app(pod.app_name)
            if app is not None:
                app.pods.append(pod)
                logger.debug(f"Cluster.update: Assign <{pod.name}> to {{{app.name}}}")
            else:
                nan_app.pods.append(pod)
                logger.debug(f"Cluster.update: Assign <{pod.name}> to {{nan}}")
