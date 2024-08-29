from ..models.types import *
from ..utils import load_obj, save_obj
from .logger import logger
from ..models import PSIModel, CTModel
import pandas as pd

ModelName = str
ModelPath = str


class InterferenceProfiler:
    def __init__(
        self,
        ls_model_data: dict[ModelName, ModelPath],
        be_model_data: dict[ModelName, ModelPath],
    ) -> None:
        self.ls_models: dict[str, PSIModel] = {}
        self.be_models: dict[str, CTModel] = {}
        for name in ls_model_data:
            path = ls_model_data[name]
            self.ls_models[name] = load_obj(path, PSIModel)
        for name in be_model_data:
            path = be_model_data[name]
            self.be_models[name] = load_obj(path, CTModel)

    def ls_profile(
        self,
        app: str,
        node_cpu_util: Utilization,
        node_mem_util: Utilization,
        pod_cpu_util: Utilization,
        pod_mem_util: Utilization,
        qps: QPS,
    ) -> PSI:
        if node_cpu_util >= 1:
            return 1.0
        if app not in self.ls_models:
            logger.debug(f"InterferenceProfiler.ls_profile: {{{app}}} not found.")
            return 0
        model = self.ls_models[app]
        x = [(node_cpu_util, node_mem_util, pod_cpu_util, pod_mem_util, qps)]
        result = model.predict(x)[0]
        return max(result, 0.0)

    def be_profile(
        self,
        app: str,
        node_cpu_util: Utilization,
        node_mem_util: Utilization,
        pod_cpu_util: Utilization,
        pod_mem_util: Utilization,
    ) -> CT:
        if node_cpu_util > 1:
            return 1.0
        if app not in self.be_models:
            logger.debug(f"InterferenceProfiler.be_profile: {{{app}}} not found.")
            return 0
        model = self.be_models[app]
        x = [(node_cpu_util, node_mem_util, pod_cpu_util, pod_mem_util)]
        result = model.predict(x)[0]
        return max(result, 0.0)

    @staticmethod
    def train_ls(pod_data_path: str, node_data_path: str, assignment_data_path: str, model_path: str) -> None:
        pod_data = pd.read_csv(pod_data_path)[
            [
                "microservice",
                "pod",
                "cpu_some_avg10",
                "cpu_usage",
                "mem_usage",
                "round",
                "throughput",
                "offline_job",
            ]
        ]
        node_data = pd.read_csv(node_data_path)[
            ["node", "node_cpu", "node_mcp", "round", "throughput", "offline_job"]
        ]
        assignment_data = pd.read_csv(assignment_data_path)
        data = pod_data.merge(assignment_data).merge(node_data)
        for app_name, grp in data.groupby("microservice"):
            if "python" in app_name:
                continue
            replicas = len(grp["pod"].unique())
            grp["throughput"] /= replicas
            y = grp["cpu_some_avg10"].tolist()
            x = grp[["node_cpu", "node_mcp", "cpu_usage", "mem_usage", "throughput"]]
            x = x.apply(lambda x: list(x), axis=1).tolist()
            model = PSIModel()
            model.train(x, y)
            save_obj(f"{model_path}/{app_name}.ls", model)

    @staticmethod
    def train_be(
        pod_data_path: str, node_data_path: str, jct_data_path: str, model_path: str
    ) -> None:
        pod_data = pd.read_csv(pod_data_path)[
            [
                "microservice",
                "pod",
                "cpu_usage",
                "mem_usage",
                "round",
                "throughput",
                "offline_job",
            ]
        ]
        node_data = pd.read_csv(node_data_path)[
            ["node", "node_cpu", "node_mcp", "round", "throughput", "offline_job"]
        ]
        jct_data = (
            pd.read_csv(jct_data_path)
            .groupby(["round", "throughput", "node", "offline_job", "pod"])["jct"]
            .mean()
            .reset_index()
        )
        data = pod_data.merge(jct_data).merge(node_data)
        y = data["jct"].tolist()
        x = data[["node_cpu", "node_mcp", "cpu_usage", "mem_usage"]]
        x = x.apply(lambda x: list(x), axis=1).tolist()
        model = CTModel()
        model.train(x, y)
        save_obj(f"{model_path}/pythonpi.be", model)
