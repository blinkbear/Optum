import threading
from time import sleep
from ..models.types import *
from ..utils.k8s import client as k8s_client
from ..models import Node, Cluster, Pod
from abc import ABC, abstractmethod


class BaselineScheduler(ABC):
    def __init__(self, cluster: Cluster) -> None:
        self.cluster_lock = threading.Lock()
        self.cluster = cluster
        self.online_qps = 0

    @abstractmethod
    def select(self, pod: Pod) -> Node:
        pass

    @abstractmethod
    def run(self):
        pass

    def _run(self, scheduler_name):
        exit_event = threading.Event()
        scheduling_thread = threading.Thread(
            target=k8s_client.schedule_pending_pods,
            args=(scheduler_name, self.select, exit_event),
        )
        monitoring_thread = threading.Thread(target=self.monitoring, args=(exit_event,))

        scheduling_thread.start()
        monitoring_thread.start()

        self.exit_event = exit_event

    def check_mem_availability(self, node: Node, pod: Pod) -> bool:
        node_mem_requested = node.get_mem_requested() + pod.mem_requests
        if node_mem_requested > node.mem_cap:
            return False
        return True

    def set_qps(self, qps: QPS):
        self.online_qps = qps

    def stop(self):
        self.exit_event.set()

    def monitoring(self, exit_event: threading.Event):
        while not exit_event.is_set():
            self.cluster_lock.acquire()
            self.cluster.update(self.online_qps)
            self.cluster_lock.release()
            sleep(5)
