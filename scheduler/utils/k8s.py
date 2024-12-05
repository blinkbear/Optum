from kubernetes import config, client, watch
from kubernetes.client.models import V1Pod, V1ObjectReference, V1Binding, V1ObjectMeta
from ..models.types import *
from ..models import Node, Pod
from . import parse_cpu_unit, parse_mem_unit
from typing import Literal, Callable
from ..utils import logger
from threading import Event
import traceback


class K8sClient:
    def __init__(self) -> None:
        config.load_kube_config()
        self.v1 = client.CoreV1Api()

    def get_all_nodes(self) -> dict[NodeName, Node]:
        results = {}
        nodes = self.v1.list_node()
        logger.debug(f"K8sClient.get_all_nodes: Get {len(nodes.items)} nodes")
        for node in nodes.items:
            ip = [x.address for x in node.status.addresses if x.type == "InternalIP"][0]
            name = node.metadata.name
            cpu_cap = parse_cpu_unit(node.status.capacity["cpu"])
            mem_cap = float(node.status.capacity["memory"][:-2]) / 1024
            py_node = Node(name, ip, cpu_cap, mem_cap)
            results[name] = py_node
        return results

    def get_pod_type(self, k8s_pod: V1Pod, app_name: str) -> Literal["be", "ls"]:
        # TODO: Here only records the app that will be used in Hotel.Search
        if app_name in ["frontend", "geo", "profile", "rate", "reservation", "search"]:
            return "ls"
        # if k8s_pod.metadata.namespace not in ["hotel-reserv", "social-network"]:
        #     return "be"
        # return "ls"
        return "be"

    def get_all_pods(self) -> dict[PodName, Pod]:
        results = {}
        pods = self.v1.list_pod_for_all_namespaces()
        logger.debug(f"K8sClient.get_all_pods: Get {len(pods.items)} pods")
        for pod in pods.items:
            optum_pod = self.parse_k8s_pod_to_optum_pod(pod)
            if optum_pod.cpu_requests == 0:
                continue
            results[optum_pod.name] = optum_pod
        return results

    def get_pod_app(self, k8s_pod: V1Pod) -> AppName:
        if "pythonpi" in k8s_pod.metadata.name:
            return "pythonpi"
        app = "-".join(k8s_pod.metadata.name.split("-")[:-2])
        return app

    def parse_k8s_pod_to_optum_pod(self, k8s_pod: V1Pod) -> Pod:
        app = self.get_pod_app(k8s_pod)
        name = k8s_pod.metadata.name
        namespace = k8s_pod.metadata.namespace
        pod_type = self.get_pod_type(k8s_pod, app)
        node_name = k8s_pod.spec.node_name
        limits = k8s_pod.spec.containers[0].resources.limits
        requests = k8s_pod.spec.containers[0].resources.requests
        cpu_requests = 0
        mem_requests = 0
        if limits is not None:
            if "cpu" in limits:
                cpu_requests = parse_cpu_unit(limits["cpu"])
            if "memory" in limits:
                mem_requests = parse_mem_unit(limits["memory"])
        if requests is not None:
            if "cpu" in requests:
                cpu_requests = parse_cpu_unit(requests["cpu"])
            if "memory" in requests:
                mem_requests = parse_mem_unit(requests["memory"])
        return Pod(
            name,
            app,
            node_name=node_name,
            type=pod_type,
            namespace=namespace,
            cpu_requests=cpu_requests,
            mem_requests=mem_requests,
        )

    def check_pod_existence(self, k8s_pod: V1Pod) -> bool:
        try:
            self.v1.read_namespaced_pod(
                name=k8s_pod.metadata.name,
                namespace=k8s_pod.metadata.namespace,
                _preload_content=False,
            )
            return True
        except:
            return False

    def schedule_pending_pods(
        self,
        scheduler_name: str,
        node_selection: Callable[[Pod], Node],
        exit_event: Event,
    ):
        watcher = watch.Watch()
        for event in watcher.stream(self.v1.list_pod_for_all_namespaces):
            if (
                event["type"] == "ADDED"
                and event["object"].status.phase == "Pending"
                and event["object"].spec.scheduler_name == scheduler_name
            ):
                try:
                    k8s_pod = event["object"]
                    if not self.check_pod_existence(k8s_pod):
                        continue
                    pod = self.parse_k8s_pod_to_optum_pod(k8s_pod)
                    node = node_selection(pod)
                    k8s_node = V1ObjectReference(
                        kind="Node",
                        api_version="v1",
                        name=node.name,
                        namespace=pod.namespace,
                    )
                    meta = V1ObjectMeta()
                    meta.name = pod.name
                    binding = V1Binding(target=k8s_node, metadata=meta)
                    self.v1.create_namespaced_binding(
                        pod.namespace, binding, _preload_content=False
                    )
                except Exception as e:
                    logger.warning(f"K8sClient.schedule_pending_pods: {e}")
                    traceback.print_exc()
            if exit_event.is_set():
                watcher.stop()


client = K8sClient()
