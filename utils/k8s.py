from kubernetes import config, client
from kubernetes.client.models.v1_pod import V1Pod
from bidict import bidict
from custom_types import *

App = str


def parse_cpu_unit(k8s_cpu_str: str) -> CPUCores:
    if k8s_cpu_str.endswith("m"):
        return float(k8s_cpu_str[:-1]) / 1000
    return float(k8s_cpu_str)


class Client:
    def __init__(self) -> None:
        config.load_kube_config()
        self.v1 = client.CoreV1Api()

    def get_pods(self, node: str) -> list[V1Pod]:
        return [
            pod
            for pod in self.v1.list_pod_for_all_namespaces().items
            if pod.spec.node_name == node
        ]

    def get_node_cpu_capacity(self, node_name: str) -> float:
        nodes = self.v1.list_node()
        for node in nodes.items:
            if node.metadata.name == node_name:
                return float(node.status.capacity["cpu"])

    def get_node_all_node_ip(self) -> bidict:
        node_ip_mapping = bidict({})
        nodes = self.v1.list_node()
        for node in nodes.items:
            ip = [x.address for x in node.status.addresses if x.type == "InternalIP"][0]
            node_name = node.metadata.name
            node_ip_mapping[node_name] = ip
        return node_ip_mapping

    def get_node_mem_capacity(self, node_name: str) -> MemInMB:
        nodes = self.v1.list_node()
        for node in nodes.items:
            if node.metadata.name == node_name:
                return float(node.status.capacity["memory"][:-2]) / 1024

    def get_node_mem_allocated(self, node_name: str) -> MemInMB:
        nodes = self.v1.list_node()
        for node in nodes.items:
            if node.metadata.name == node_name:
                capacity = float(node.status.capacity["memory"][:-2]) / 1024
                allocatable = float(node.status.allocatable["memory"][:-2]) / 1024
                return capacity - allocatable

    def get_all_pod_cpu_quota(
        self, node_name: str
    ) -> dict[str, dict[str, App | CPUCores]]:
        results = {}
        for pod in self.v1.list_pod_for_all_namespaces().items:
            if pod.spec.node_name != node_name:
                continue
            limits = pod.spec.containers[0].resources.limits
            if limits is None or "cpu" not in limits:
                continue
            cpu_quota = parse_cpu_unit(limits["cpu"])
            app = pod.metadata.labels.get("app", "nan")
            app = pod.metadata.labels.get("app-name", app)
            results[pod.metadata.name] = {"app": app, "cpu_quota": cpu_quota}
        return results


client = Client()
