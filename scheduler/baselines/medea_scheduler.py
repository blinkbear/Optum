from .base import BaselineScheduler
from ..models.types import *
from ..models import Node, Cluster, Pod

SCHEDULER_NAME = "medea-scheduler"


def solve(r_C, r_M, Rf_C, Rf_M, w1, w2):
    import numpy as np
    import scipy.optimize as opt

    k = len(r_C)
    N = len(Rf_C)
    rmin_C = min(r_C)
    rmin_M = min(r_M)

    n = k + N + k * N
    B = 1000
    c = np.array([w1 / k] * k + [w2 / N] * N + [0] * k * N)
    Xtmp = np.array([])
    A1 = np.array([])
    for i in range(k):
        Xtmp = np.concatenate(
            (Xtmp, np.array([0] * (i * N) + [1] * N + [0] * (k - i - 1) * N))
        )
    Xtmp = np.reshape(Xtmp, (k, k * N))
    A1 = np.hstack((np.zeros((k, k + N)), Xtmp))
    b1 = np.array([1] * k)
    R_Ctmp = np.array([])
    R_Mtmp = np.array([])
    for j in range(k):
        resource = np.identity(N) * r_C[j]
        if len(R_Ctmp) == 0:
            R_Ctmp = resource
        else:
            R_Ctmp = np.hstack((R_Ctmp, resource))
        resource = np.identity(N) * r_M[j]
        if len(R_Mtmp) == 0:
            R_Mtmp = resource
        else:
            R_Mtmp = np.hstack((R_Mtmp, resource))

    b1 = np.array([1] * k)
    A2_C = np.hstack((np.zeros((N, k)), np.zeros((N, N)), R_Ctmp))
    b2_C = np.array(Rf_C)
    A2_M = np.hstack((np.zeros((N, k)), np.zeros((N, N)), R_Mtmp))
    b2_M = np.array(Rf_M)
    A3 = np.hstack((-1 * np.identity(k), np.zeros((k, N)), Xtmp))
    b3 = np.array([0] * k)
    A4_C = np.hstack((np.zeros((N, k)), np.identity(N) * B, R_Ctmp))
    b4_C = np.array(Rf_C) - np.array([rmin_C] * N) + np.array([B] * N)
    A4_M = np.hstack((np.zeros((N, k)), np.identity(N) * B, R_Mtmp))
    b4_M = np.array(Rf_M) - np.array([rmin_M] * N) + np.array([B] * N)
    func = lambda x: -1 * np.dot(c, x)
    cons = (
        {"type": "eq", "fun": lambda x: np.dot(A1, x) - b1},
        {"type": "ineq", "fun": lambda x: b2_C - np.dot(A2_C, x)},
        {"type": "ineq", "fun": lambda x: b2_M - np.dot(A2_M, x)},
        {"type": "eq", "fun": lambda x: np.dot(A3, x) - b3},
        {"type": "ineq", "fun": lambda x: b4_C - np.dot(A4_C, x)},
        {"type": "ineq", "fun": lambda x: b4_M - np.dot(A4_M, x)},
    )
    bounds = opt.Bounds([0] * n, [1] * n)
    res = opt.minimize(
        func, np.zeros(n), method="SLSQP", constraints=cons, bounds=bounds
    )
    result = []
    for i in range(k):
        start = k + N + i * N
        end = k + N + (i + 1) * N
        p = res.x[start:end]
        p = np.array(p)
        p[p < 0] = 0
        total_p = np.sum(p)
        max_p_index = np.where(p == np.max(p))[0]
        if total_p < 1:
            p[-1] = 1 - np.sum(p[:-1])
        elif total_p > 1:
            p[max_p_index] = p[max_p_index] - (total_p - 1)
        if np.sum(p) == 1:
            if any(map(lambda x: x < 0, p)):
                result.append(np.random.choice([i for i in range(N)]))
            else:
                result.append(np.random.choice([i for i in range(N)], p=p.ravel()))
        else:
            result.append(np.random.choice([i for i in range(N)]))
    return result


class MedeaScheduler(BaselineScheduler):
    def __init__(self, cluster: Cluster, w1: float = 1.0, w2: float = 0.25) -> None:
        super().__init__(cluster)
        self.w1 = w1
        self.w2 = w2

    def select(self, pod: Pod) -> Node:
        self.cluster_lock.acquire()
        # Since the experiment cluster is not large, we don't partition the cluster.
        nodes = list(self.cluster.nodes.values())
        node_cpu_free = [x.cpu_cap - x.get_cpu_usage() for x in nodes]
        node_mem_free = [x.mem_cap - x.get_mem_requested() for x in nodes]
        result = solve(
            # CPU requests of all pods
            [pod.cpu_requests],
            # mem requests of all pods
            [pod.mem_requests],
            # available CPU of all nodes
            node_cpu_free,
            # available mem of all nodes
            node_mem_free,
            self.w1,
            self.w2,
        )
        self.cluster_lock.release()
        return nodes[result[0]]

    def run(self):
        super()._run(SCHEDULER_NAME)
