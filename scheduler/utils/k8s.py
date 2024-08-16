from kubernetes import config, client
from kubernetes.client.models.v1_pod import V1Pod
from ..models.types import *
from ..models import Node, Pod
from . import parse_cpu_unit
from typing import Literal


class Client:
    def __init__(self) -> None:
        config.load_kube_config()
        self.v1 = client.CoreV1Api()

    def get_all_nodes(self) -> dict[NodeName, Node]:
        results = {}
        nodes = self.v1.list_node()
        for node in nodes.items:
            ip = [x.address for x in node.status.addresses if x.type == "InternalIP"][0]
            name = node.metadata.name
            cpu_cap = parse_cpu_unit(node.status.capacity["cpu"])
            mem_cap = float(node.status.capacity["memory"][:-2]) / 1024
            py_node = Node(name, ip, cpu_cap, mem_cap)
        results[name] = py_node
        return results

    def get_pod_type(self, k8s_pod: V1Pod, app_name: str) -> Literal["be", "ls"]:
        if k8s_pod.metadata.namespace not in ["hotel-reserv", "social-network"]:
            return "be"
        if app_name == "nan":
            return "be"
        return "ls"

    def get_all_pods(self) -> dict[PodName, Pod]:
        results = {}
        pods = self.v1.list_pod_for_all_namespaces()
        for pod in pods.items:
            app = self.get_pod_app(pod)
            name = pod.metadata.name
            namespace = pod.metadata.namespace
            pod_type = self.get_pod_type(pod, app)
            node_name = pod.spec.node_name
            limits = pod.spec.containers[0].resources.limits
            if limits is None or "cpu" not in limits:
                continue
            cpu_requests = parse_cpu_unit(limits["cpu"])
            results[name] = Pod(
                name,
                app,
                node_name=node_name,
                type=pod_type,
                namespace=namespace,
                cpu_requests=cpu_requests,
            )
        return results

    def get_pod_app(self, k8s_pod: V1Pod) -> AppName:
        if "pythonpi" in k8s_pod.metadata.name:
            return "pythonpi"
        app = k8s_pod.metadata.labels.get("app", "nan")
        app = k8s_pod.metadata.labels.get("app-name", app)
        return app

    def get_pod_app_by_name(self, pod_name: str, namespace: str) -> AppName:
        pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        return self.get_pod_app(pod)


client = Client()
