from ..models.types import *
from .interference_predictor import InterferencePredictor
from .resource_usage_predictor import ResourceUsagePredictor
from ..models import Node, Pod, Cluster


class Scheduler:
    def __init__(
        self,
        cluster: Cluster,
        inf_predictor: InterferencePredictor,
        res_predictor: ResourceUsagePredictor,
        online_weight: float = 0.5,
        offline_weight: float = 0.5,
    ) -> None:
        self.cluster = cluster
        self.online_weight = online_weight
        self.offline_weight = offline_weight
        self.inf_predictor = inf_predictor
        self.res_predictor = res_predictor
        self.pods_cached: dict[NodeName, list[Pod]] = {}

    def score(
        self,
        node: Node,
        new_pod: Pod,
    ) -> NodeScore:
        # Equation (11)
        pods: list[Pod] = (
            list(node.pods.values()) + self.pods_cached.get(node.name, []) + [new_pod]
        )
        poc = self.res_predictor.get_poc(pods)
        pom = self.res_predictor.get_pom(pods)
        node_cpu_cap, node_mem_cap = node.cpu_cap, node.mem_cap
        node_cpu_util = poc / node_cpu_cap
        node_mem_util = pom / node_mem_cap
        ct_sum, psi_sum = [], []
        for pod in pods:
            app_name = pod.app_name
            app = self.cluster.get_app(app_name)
            pod_cpu_util = app.get_p95_pod_cpu_util()
            pod_mem_util = app.get_p95_pod_mem_util()
            qps = app.qps / app.get_pod_counts()
            if pod.type == "be":
                ct = self.inf_predictor.get_ri_ct(
                    app_name,
                    pod_cpu_util,
                    pod_mem_util,
                    node_cpu_util,
                    node_mem_util,
                )
                ct_sum.append(ct)
            elif pod.type == "ls":
                psi = self.inf_predictor.get_ri_psi(
                    app_name,
                    pod_cpu_util,
                    pod_mem_util,
                    node_cpu_util,
                    node_mem_util,
                    qps,
                )
                psi_sum.append(psi)
        ct_sum, psi_sum = sum(ct_sum), sum(psi_sum)
        score = (
            node_cpu_util * node_mem_util
            - self.online_weight * psi_sum
            - self.offline_weight * ct_sum
        )
        return score

    def schedule(self, new_pods: list[Pod], online_qps: QPS) -> dict[PodName, Node]:
        # update cluster status
        self.cluster.update(online_qps)
        scheduling_outcome: dict[PodName, Node] = {}
        for pod in new_pods:
            max_score, selected_node = -200, None
            for node in self.cluster.nodes.values():
                score = self.score(node, pod)
                if score > max_score:
                    max_score = score
                    selected_node = node
            # Update cache
            self.pods_cached[selected_node.name] = self.pods_cached.get(
                selected_node.name, []
            ) + [pod]
            scheduling_outcome[pod.name] = selected_node
        # Reset cache
        self.pods_cached.clear()
        return scheduling_outcome
