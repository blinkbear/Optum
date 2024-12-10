from ..models.types import *
from .interference_predictor import InterferencePredictor
from .resource_usage_predictor import ResourceUsagePredictor
from ..models import Node, Pod, Cluster
from .logger import logger
from ..utils.k8s import client as k8s_client
from typing import Callable
from time import sleep
import threading

SCHEDULER_NAME = "optum-scheduler"


class Scheduler:
    def __init__(
        self,
        cluster: Cluster,
        inf_predictor: InterferencePredictor,
        res_predictor: ResourceUsagePredictor,
        pred_data_handler: Callable[[OptumPredData], None] | None = None,
        online_weight: float = 0.7,
        offline_weight: float = 0.3,
    ) -> None:
        self.cluster = cluster
        self.online_weight = online_weight
        self.offline_weight = offline_weight
        self.inf_predictor = inf_predictor
        self.res_predictor = res_predictor
        self.online_qps = 0
        self.cluster_lock = threading.Lock()
        default_pred_data_handler: Callable[[OptumPredData], None] = lambda _: None
        self.pred_data_handler = (
            pred_data_handler
            if pred_data_handler is not None
            else default_pred_data_handler
        )

    def score(
        self,
        node: Node,
        new_pod: Pod,
    ) -> NodeScore:
        # Equation (11)
        pods: list[Pod] = list(node.pods.values()) + [new_pod]
        # If requested CPU > Node CPU capacity, skip
        cpu_sum = sum([x.cpu_requests for x in pods])
        if cpu_sum > node.cpu_cap:
            return -200
        poc = self.res_predictor.get_poc(pods)
        logger.debug(
            f"Scheduler.score: POC of <{new_pod.name}> on [{node.name}] is {poc}"
        )
        pom = self.res_predictor.get_pom(pods)
        logger.debug(
            f"Scheduler.score: POM of <{new_pod.name}> on [{node.name}] is {pom}"
        )
        node_cpu_cap, node_mem_cap = node.cpu_cap, node.mem_cap
        node_cpu_util = poc / node_cpu_cap
        node_mem_util = pom / node_mem_cap
        ct_sum, psi_sum = [], []
        for pod in pods:
            app_name = pod.app_name
            app = self.cluster.get_app(app_name)
            pod_cpu_util = app.get_p95_pod_cpu_util()
            pod_mem_util = app.get_p95_pod_mem_util()
            if pod.type == "be":
                ct = self.inf_predictor.get_ri_ct(
                    app_name,
                    pod_cpu_util,
                    pod_mem_util,
                    node_cpu_util,
                    node_mem_util,
                )
                logger.debug(f"Scheduler.score: Computed CT for <{pod.name}> is {ct}")
                ct_sum.append(ct)
                pred_performance_metric = ct
            elif pod.type == "ls":
                qps = app.qps / app.get_pod_counts()
                psi = self.inf_predictor.get_ri_psi(
                    app_name,
                    pod_cpu_util,
                    pod_mem_util,
                    node_cpu_util,
                    node_mem_util,
                    qps,
                )
                logger.debug(f"Scheduler.score: Computed PSI for <{pod.name}> is {psi}")
                psi_sum.append(psi)
                pred_performance_metric = psi
            # These data are used to report prediction result.
            data = OptumPredData(
                pod.name,
                pod.app_name,
                pod.type,
                pred_performance_metric,
                node_cpu_util,
                node_mem_util,
            )
        ct_sum, psi_sum = sum(ct_sum), sum(psi_sum)
        score = (
            node_cpu_util * node_mem_util
            - self.online_weight * psi_sum
            - self.offline_weight * ct_sum
        )
        return score, data

    def select(self, pod: Pod) -> Node:
        self.cluster_lock.acquire()
        max_score, selected_node = None, None
        final_pred_data = None
        for node in self.cluster.nodes.values():
            score, pred_data = self.score(node, pod)
            logger.debug(f"Scheduler.score:Node {node.name} get score {score}")
            if max_score is None or score > max_score:
                max_score = score
                selected_node = node
                final_pred_data = pred_data
        logger.info(
            f"Scheduler.schedule: Final selection of <{pod.name}> is [{selected_node.name}]"
        )
        self.cluster.assign_pod_to_node(pod, selected_node)
        self.cluster_lock.release()
        if final_pred_data is not None:
            self.pred_data_handler(final_pred_data)
        return selected_node

    def monitoring(self, exit_event: threading.Event):
        while not exit_event.is_set():
            self.cluster_lock.acquire()
            self.cluster.update(self.online_qps)
            self.res_predictor.update(self.cluster.nodes.values())
            self.cluster_lock.release()
            sleep(10)

    def run(self):
        exit_event = threading.Event()
        scheduling_thread = threading.Thread(
            target=k8s_client.schedule_pending_pods,
            args=(SCHEDULER_NAME, self.select, exit_event),
        )
        monitoring_thread = threading.Thread(target=self.monitoring, args=(exit_event,))

        scheduling_thread.start()
        monitoring_thread.start()

        self.exit_event = exit_event

    def stop(self):
        self.exit_event.set()

    def set_qps(self, online_qps: QPS):
        self.online_qps = online_qps
        logger.info(f"Scheduler.set_qps: QPS is set to {online_qps}")
