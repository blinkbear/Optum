from kubernetes import config, client
from kubernetes.client.models.v1_pod import V1Pod
from bidict import bidict


MemInMB = float


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

    def get_cpu_capacity(self, node_name: str) -> float:
        nodes = self.v1.list_node()
        for node in nodes.items:
            if node.metadata.name == node_name:
                return float(node.status.capacity["cpu"])
    
    def get_all_node_ip(self) -> bidict:
        node_ip_mapping = bidict({})
        nodes = self.v1.list_node()
        for node in nodes.items:
            ip = [x.address for x in node.status.addresses if x.type == "InternalIP"][0]
            node_name = node.metadata.name
            node_ip_mapping[node_name] = ip
        return node_ip_mapping

    def get_mem_capacity(self, node_name: str) -> MemInMB:
        nodes = self.v1.list_node()
        for node in nodes.items:
            if node.metadata.name == node_name:
                return float(node.status.capacity["memory"][:-2]) / 1024
    
    def get_mem_allocated(self, node_name: str) -> MemInMB:
        nodes = self.v1.list_node()
        for node in nodes.items:
            if node.metadata.name == node_name:
                capacity = float(node.status.capacity["memory"][:-2]) / 1024
                allocatable = float(node.status.allocatable["memory"][:-2]) / 1024
                return capacity - allocatable


client = Client()
