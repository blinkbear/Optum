from .base import BaselineScheduler
from random import choice
from ..models import Cluster, Pod, Node
from ..models.types import *
from logging import getLogger

logger = getLogger("ResourceCentral")

SCHEDULER_NAME = "resource-central-scheduler"


class ResourceCentralScheduler(BaselineScheduler):
    def __init__(
        self, cluster: Cluster, max_util: float = 0.8, over_commit: float = 1.2
    ) -> None:
        super().__init__(cluster)
        self.MAX_UTIL = max_util
        self.OVER_COMMIT = over_commit

    def select(self, pod: Pod) -> Node:
        self.cluster_lock.acquire()
        available_nodes: list[Node] = []
        # Generate a predicted CPU usage for pod.
        # Because after assigning pod to node, node need this data to compute
        # its CPU usage.
        pod.cpu_usage = (
            self.cluster.get_app(pod.app_name).get_p95_pod_cpu_util() * pod.cpu_requests
        )
        for node in self.cluster.nodes.values():
            if not self.check_mem_avalability():
                continue
            # Check CPU availability
            node_requested_cpu = node.get_cpu_requested()
            node_cpu_usage = node.get_cpu_usage()
            if pod.type == "ls":
                request_condition = (
                    node_requested_cpu + pod.cpu_requests <= node.cpu_cap
                )
                util_condition = True
            else:
                request_condition = (
                    node_requested_cpu + pod.cpu_requests
                    <= self.OVER_COMMIT * node.cpu_cap
                )
                util_condition = (
                    pod.cpu_usage + node_cpu_usage <= self.MAX_UTIL * node.cpu_cap
                )
            if request_condition and util_condition:
                available_nodes.append(node)
        selected_node = choice(available_nodes)
        self.cluster.assign_pod_to_node(pod, selected_node)
        self.cluster_lock.release()
        logger.info(f"Final selection of <{pod.name}> is [{selected_node.name}]")
        return selected_node

    def run(self):
        super()._run(SCHEDULER_NAME)
