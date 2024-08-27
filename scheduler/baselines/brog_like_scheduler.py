from .base import BaselineScheduler
from ..models.types import *
from ..models import Cluster, Node, Pod
from random import choice
from logging import getLogger

logger = getLogger("BrogLike")

SCHEDULER_NAME = "brog-like-scheduler"


class BrogLikeScheduler(BaselineScheduler):
    def __init__(self, cluster: Cluster, pred_pod_util: Utilization = 0.8) -> None:
        super().__init__(cluster)
        self.pred_pod_util = pred_pod_util

    def select(self, pod: Pod) -> Node:
        available_nodes: list[Node] = []
        self.cluster_lock.acquire()
        for node in self.cluster.nodes.values():
            if not self.check_mem_avalability():
                continue
            # Check CPU availability
            node_cpu_usage = (
                pod.cpu_requests + node.get_cpu_requested()
            ) * self.pred_pod_util
            if node_cpu_usage <= node.cpu_cap:
                available_nodes.append(node)
        selected_node = choice(available_nodes)
        self.cluster.assign_pod_to_node(pod, selected_node)
        self.cluster_lock.release()
        logger.info(f"Final selection of <{pod.name}> is [{selected_node.name}]")
        return selected_node

    def run(self):
        super()._run(SCHEDULER_NAME)
