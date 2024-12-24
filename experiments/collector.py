from AEFM.data_collector.jaeger_trace_collector import JaegerTraceCollector
from AEFM.data_collector.models import CpuUsage, MemUsage
from AEFM.data_collector.wrk_throughput_collector import WrkThroughputCollector
import pandas as pd
from AEFM.data_collector.base import BaseDataCollector, Collection
from AEFM.utils.logger import log
from AEFM.data_collector.prom_hardware_collector import PromHardwareCollector
from AEFM.models import Node
from statistics import mean
from scheduler.models.types import OptumPredData


class MyPromCollector(PromHardwareCollector):
    def collect_node_cpu(self, nodes: list[Node], start_time, end_time):
        ips = [node.ip for node in nodes]
        constraint = ":9100|".join(ips) + ":9100"
        query = (
            "1 - avg without(cpu) (sum without(mode) (rate(node_cpu_seconds_total"
            f'{{job="node-exporter",mode=~"idle|iowait|steal",instance=~"{constraint}"}}'
            "[90s])))"
        )
        response = self.fetcher.fetch(query, "range", 1, start_time, end_time)
        log.debug(
            f"{__file__}: Fetch Node CPU usage from: {response.url}", to_file=True
        )
        usage = response.json()
        records = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                ip = str(data["metric"]["instance"]).split(":")[0]
                usage = mean([float(v[1]) for v in data["values"]])
                node = [n.name for n in nodes if n.ip == ip][0]
                records.append({"node": node, "node_cpu": usage})
        return pd.DataFrame(records)

    def collect_node_mcp(self, nodes: list[Node], start_time, end_time):
        ips = [node.ip for node in nodes]
        constraint = ":9100|".join(ips) + ":9100"
        query = f'instance:node_memory_utilisation:ratio{{instance=~"{constraint}"}}'
        response = self.fetcher.fetch(query, "range", 1, start_time, end_time)
        log.debug(
            f"{__file__}: Fetch Node MCP usage from: {response.url}", to_file=True
        )
        usage = response.json()
        records = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                ip = str(data["metric"]["instance"]).split(":")[0]
                usage = max([float(v[1]) for v in data["values"]])
                node = [n.name for n in nodes if n.ip == ip][0]
                records.append({"node": node, "node_mcp": usage})
        return pd.DataFrame(records)

    def collect_node_net(self, nodes: list[Node], start_time, end_time):
        ips = [node.ip for node in nodes]
        constraint = ":9100|".join(ips) + ":9100"
        query = f'sum(irate(node_network_transmit_bytes_total{{instance=~"{constraint}"}}[1m])) by (instance) / 1024 / 1024'
        response = self.fetcher.fetch(query, "range", 1, start_time, end_time)
        log.debug(
            f"{__file__}: Fetch Node Net usage from: {response.url}", to_file=True
        )
        usage = response.json()
        records = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                ip = str(data["metric"]["instance"]).split(":")[0]
                usage = max([float(v[1]) for v in data["values"]])
                node = [n.name for n in nodes if n.ip == ip][0]
                records.append({"node": node, "node_net": usage})
        return pd.DataFrame(records)

    def collect_node_psi(self, nodes: list[Node], start_time, end_time):
        query = f'node_psi{{node=~"{"|".join([x.name for x in nodes])}"}}'
        response = self.fetcher.fetch(query, "range", 1, start_time, end_time)
        log.debug(
            f"{__file__}: Fetch Node PSI usage from: {response.url}", to_file=True
        )
        usage = response.json()
        results = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                node = str(data["metric"]["node"])
                resource = str(data["metric"]["resource"])
                type = str(data["metric"]["type"])
                window = str(data["metric"]["window"])
                value = mean([float(v[1]) for v in data["values"]])
                results.append(
                    {
                        "node": node,
                        "resource": resource,
                        "type": type,
                        "window": window,
                        "value": value,
                    }
                )
        results = pd.DataFrame(results)
        node_names = [x.name for x in nodes]
        processed_results = []
        for node_name in node_names:
            data = results.loc[results["node"] == node_name]
            data = data.sort_values(["resource", "type", "window"])
            data["name"] = data["resource"] + "_" + data["type"] + "_" + data["window"]
            data = {x: y for x, y in zip(data["name"].tolist(), data["value"].tolist())}
            data["node"] = node_name
            processed_results.append(data)
        return pd.DataFrame(processed_results)

    def collect_cpu_usage(
        self, microservices: list[str], start_time: float, end_time: float
    ) -> CpuUsage:
        microservices.append("pythonpi")
        constraint = 'pod=~"' + ".*|".join(microservices) + '.*"'
        # ! Hardcode, 0.1 = pod CPU requests/limits
        query = f"irate(container_cpu_usage_seconds_total{{{constraint}}}[1m]) / 1.5"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch CPU usage from: {response.url}", to_file=True)
        usage = response.json()
        cpu_usage = CpuUsage()
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                pod = str(data["metric"]["pod"])
                microservice = "-".join(pod.split("-")[:-2])
                value = max([float(v[1]) for v in data["values"]])
                cpu_usage.set(microservice, pod, value)
        return cpu_usage

    def collect_mem_usage(
        self, microservices: list[str], start_time: float, end_time: float
    ) -> MemUsage:
        microservices.append("pythonpi")
        constraint = 'pod=~"' + ".*|".join(microservices) + '.*"'
        # ! Hardcode, 100 = pod mem requests/limits
        query = f"container_memory_usage_bytes{{{constraint}}} / 1024 / 1024 / 200"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch Mem usage from: {response.url}", to_file=True)
        usage = response.json()
        mem_usage = MemUsage()
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                pod = str(data["metric"]["pod"])
                microservice = "-".join(pod.split("-")[:-2])
                value = max([float(v[1]) for v in data["values"]])
                mem_usage.set(microservice, pod, value)
        return mem_usage

    def collect_pod_cpu_psi(
        self, microservices: list[str], start_time: float, end_time: float
    ) -> pd.DataFrame:
        microservices.append("pythonpi")
        constraint = 'window!="total",pod_name=~"' + ".*|".join(microservices) + '.*"'
        query = f"psi_perf_monitor_monitored_cpu_psi{{{constraint}}}"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch pod CPU PSI from: {response.url}", to_file=True)
        usage = response.json()
        results = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                pod = str(data["metric"]["pod_name"])
                microservice = "-".join(pod.split("-")[:-2])
                type = str(data["metric"]["type"])
                window = "avg" + str(data["metric"]["window"])[:-1]
                value = mean([float(v[1]) for v in data["values"]])
                results.append(
                    {
                        "microservice": microservice,
                        "pod": pod,
                        "type": type,
                        "window": window,
                        "value": value,
                    }
                )
        results = pd.DataFrame(results)
        pod_names = results["pod"].unique().tolist()
        processed_results = []
        for pod_name in pod_names:
            data = results.loc[results["pod"] == pod_name]
            data = data.sort_values(["type", "window"])
            data["name"] = "cpu_" + data["type"] + "_" + data["window"]
            data = {x: y for x, y in zip(data["name"].tolist(), data["value"].tolist())}
            data["pod"] = pod_name
            processed_results.append(data)
        return pd.DataFrame(processed_results)

    def collect_pod_mem_psi(
        self, microservices: list[str], start_time: float, end_time: float
    ) -> pd.DataFrame:
        microservices.append("pythonpi")
        constraint = 'window!="total",pod_name=~"' + ".*|".join(microservices) + '.*"'
        query = f"psi_perf_monitor_monitored_mem_psi{{{constraint}}}"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch pod Mem PSI from: {response.url}", to_file=True)
        usage = response.json()
        results = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                pod = str(data["metric"]["pod_name"])
                microservice = "-".join(pod.split("-")[:-2])
                type = str(data["metric"]["type"])
                window = "avg" + str(data["metric"]["window"])[:-1]
                value = mean([float(v[1]) for v in data["values"]])
                results.append(
                    {
                        "microservice": microservice,
                        "pod": pod,
                        "type": type,
                        "window": window,
                        "value": value,
                    }
                )
        results = pd.DataFrame(results)
        pod_names = results["pod"].unique().tolist()
        processed_results = []
        for pod_name in pod_names:
            data = results.loc[results["pod"] == pod_name]
            data = data.sort_values(["type", "window"])
            data["name"] = "memory_" + data["type"] + "_" + data["window"]
            data = {x: y for x, y in zip(data["name"].tolist(), data["value"].tolist())}
            data["pod"] = pod_name
            processed_results.append(data)
        return pd.DataFrame(processed_results)

    def collect_pod_cpi(self, start_time: float, end_time: float):
        query = f"max(psi_perf_monitor_cpu_cycles) by (pod_name) / max(psi_perf_monitor_instruction) by (pod_name)"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch pod CPI from: {response.url}", to_file=True)
        cpi = response.json()
        results = []
        if cpi["data"] and cpi["data"]["result"]:
            for data in cpi["data"]["result"]:
                pod = str(data["metric"]["pod_name"])
                microservice = "-".join(pod.split("-")[:-2])
                pod_cpi = [float(v[1]) for v in data["values"] if v != "NaN"][-1]
                results.append(
                    {
                        "microservice": microservice,
                        "pod": pod,
                        "pod_cpi": pod_cpi,
                    }
                )
        return pd.DataFrame(results)

    def collect_node_cpi(self, nodes: list[Node], start_time: float, end_time: float):
        query = f"sum(node_perf_branch_instructions_total) by (instance) /sum(node_perf_cpucycles_total) by (instance)"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch node CPI from: {response.url}", to_file=True)
        cpi = response.json()
        results = []
        if cpi["data"] and cpi["data"]["result"]:
            for data in cpi["data"]["result"]:
                ip = str(data["metric"]["instance"]).split(":")[0]
                node_cpi = max([float(v[1]) for v in data["values"]])
                try:
                    node = [n.name for n in nodes if n.ip == ip][0]
                    results.append({"node": node, "node_cpi": node_cpi})
                except:
                    continue
        return pd.DataFrame(results)

    def collect_pod_io_psi(
        self, microservices: list[str], start_time: float, end_time: float
    ) -> pd.DataFrame:
        microservices.append("pythonpi")
        constraint = 'window!="total",pod_name=~"' + ".*|".join(microservices) + '.*"'
        query = f"psi_perf_monitor_monitored_io_psi{{{constraint}}}"
        response = self.fetcher.fetch(
            query, "range", step=1, start_time=start_time, end_time=end_time
        )
        log.debug(f"{__file__}: Fetch pod IO PSI from: {response.url}", to_file=True)
        usage = response.json()
        results = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                pod = str(data["metric"]["pod_name"])
                microservice = "-".join(pod.split("-")[:-2])
                type = str(data["metric"]["type"])
                window = "avg" + str(data["metric"]["window"])[:-1]
                value = mean([float(v[1]) for v in data["values"]])
                results.append(
                    {
                        "microservice": microservice,
                        "pod": pod,
                        "type": type,
                        "window": window,
                        "value": value,
                    }
                )
        results = pd.DataFrame(results)
        pod_names = results["pod"].unique().tolist()
        processed_results = []
        for pod_name in pod_names:
            data = results.loc[results["pod"] == pod_name]
            data = data.sort_values(["type", "window"])
            data["name"] = "io_" + data["type"] + "_" + data["window"]
            data = {x: y for x, y in zip(data["name"].tolist(), data["value"].tolist())}
            data["pod"] = pod_name
            processed_results.append(data)
        return pd.DataFrame(processed_results)

    def collect_pod_cpu_max_min_mean(
        self, microservices: list[str], start_time: float, end_time: float
    ):
        response = self.fetcher.fetch_cpu_usage(microservices, start_time, end_time)
        log.debug(f"{__file__}: Fetch CPU usage from: {response.url}", to_file=True)
        usage = response.json()
        records = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                pod = str(data["metric"]["pod"])
                microservice = "-".join(pod.split("-")[:-2])
                usage_max = max([float(v[1]) for v in data["values"]])
                usage_min = min([float(v[1]) for v in data["values"]])
                usage_mean = mean([float(v[1]) for v in data["values"]])
                records.append(
                    {
                        "microservice": microservice,
                        "pod": pod,
                        "pod_cpu_max": usage_max,
                        "pod_cpu_mean": usage_mean,
                        "pod_cpu_min": usage_min,
                    }
                )
        return pd.DataFrame(records)

    def collect_node_cpu_min_max_mean(self, nodes: list[Node], start_time, end_time):
        ips = [node.ip for node in nodes]
        constraint = ":9100|".join(ips) + ":9100"
        query = (
            "1 - avg without(cpu) (sum without(mode) (rate(node_cpu_seconds_total"
            f'{{job="node-exporter",mode=~"idle|iowait|steal",instance=~"{constraint}"}}'
            "[90s])))"
        )
        response = self.fetcher.fetch(query, "range", 1, start_time, end_time)
        log.debug(
            f"{__file__}: Fetch Node CPU usage from: {response.url}", to_file=True
        )
        usage = response.json()
        records = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                ip = str(data["metric"]["instance"]).split(":")[0]
                usage_mean = mean([float(v[1]) for v in data["values"]])
                usage_max = max([float(v[1]) for v in data["values"]])
                usage_min = min([float(v[1]) for v in data["values"]])
                node = [n.name for n in nodes if n.ip == ip][0]
                records.append(
                    {
                        "node": node,
                        "node_cpu_mean": usage_mean,
                        "node_cpu_max": usage_max,
                        "node_cpu_min": usage_min,
                    }
                )
        return pd.DataFrame(records)


class MyDataCollector(BaseDataCollector):
    def __init__(
        self,
        data_path: str,
        trace_collector: JaegerTraceCollector,
        hardware_collector: MyPromCollector,
        throughput_collector: WrkThroughputCollector,
        nodes: list[Node],
        offline_job_output_path: str,
        max_processes: int = 10,
        collections: list[str] = ["node_data"],
    ) -> None:
        super().__init__(
            data_path,
            trace_collector,
            hardware_collector,
            throughput_collector,
            max_processes,
        )
        self.nodes = nodes
        self.offline_job_output_path = offline_job_output_path
        self.optum_pred_data: list[OptumPredData] = []

        pod_cpi_data = Collection(
            "Pod CPI",
            f"{self.data_path}/pod_cpi_data.csv",
            self.collect_pod_cpi,
        )
        jct_data = Collection(
            "JCT data",
            f"{self.data_path}/jct_data.csv",
            self.collect_jct,
        )
        node_data = Collection(
            "node data",
            f"{self.data_path}/node_data.csv",
            self.collect_node,
        )
        optum_pred_data = Collection(
            "Optum prediction data",
            f"{self.data_path}/optum_pred_data.csv",
            self.collect_optum_pred_data,
        )
        node_min_mean_max = Collection(
            "node min mean max",
            f"{self.data_path}/node_min_mean_max.csv",
            self.collect_node_min_max_mean,
        )
        pod_min_mean_max = Collection(
            "pod min mean max",
            f"{self.data_path}/pod_min_mean_max.csv",
            self.collect_pod_min_max_mean,
        )
        pod_psi_data = Collection(
            "pod PSI data",
            f"{self.data_path}/pod_psi_data.csv",
            self.collect_pod_psi,
        )
        if "node_data" in collections:
            self.add_new_collections(node_data)
        if "optum_pred_data" in collections:
            self.add_new_collections(optum_pred_data)
        if "min_mean_max" in collections:
            self.add_new_collections([node_min_mean_max, pod_min_mean_max])
        if "jct_data" in collections:
            self.add_new_collections(jct_data)
        if "pod_cpi_data" in collections:
            self.add_new_collections(pod_cpi_data)
        if "pod_psi_data" in collections:
            self.add_new_collections(pod_psi_data)

    def collect_node_min_max_mean(self):
        start_time = self.test_case_data.start_time
        end_time = self.test_case_data.end_time
        assert isinstance(self.hardware_collector, MyPromCollector)

        return self.hardware_collector.collect_node_cpu_min_max_mean(
            self.nodes, start_time, end_time
        )

    def collect_pod_min_max_mean(self):
        start_time = self.test_case_data.start_time
        end_time = self.test_case_data.end_time
        assert isinstance(self.hardware_collector, MyPromCollector)

        microservices = self.statistical_data["microservice"].dropna().unique().tolist()
        return self.hardware_collector.collect_pod_cpu_max_min_mean(
            microservices, start_time, end_time
        )

    def collect_node(self) -> pd.DataFrame:
        start_time = self.test_case_data.start_time
        end_time = self.test_case_data.end_time
        assert isinstance(self.hardware_collector, MyPromCollector)

        cpu = self.hardware_collector.collect_node_cpu(self.nodes, start_time, end_time)
        mcp = self.hardware_collector.collect_node_mcp(self.nodes, start_time, end_time)
        # net = self.hardware_collector.collect_node_net(self.nodes, start_time, end_time)
        # psi = self.hardware_collector.collect_node_psi(self.nodes, start_time, end_time)
        # Stop collecting CPI since heavy overhead
        # cpi = self.hardware_collector.collect_node_cpi(self.nodes, start_time, end_time)
        # return cpu.merge(mcp).merge(net).merge(psi).merge(cpi)
        return cpu.merge(mcp)

    def collect_pod_cpi(self) -> pd.DataFrame:
        start_time = self.test_case_data.start_time
        end_time = self.test_case_data.end_time
        assert isinstance(self.hardware_collector, MyPromCollector)
        pod_cpi = self.hardware_collector.collect_pod_cpi(start_time, end_time)
        return pod_cpi

    def collect_pod_psi(self) -> pd.DataFrame:
        start_time = self.test_case_data.start_time
        end_time = self.test_case_data.end_time
        microservices = self.statistical_data["microservice"].dropna().unique().tolist()
        assert isinstance(self.hardware_collector, MyPromCollector)

        pod_cpu_psi = self.hardware_collector.collect_pod_cpu_psi(
            microservices, start_time, end_time
        )
        pod_mem_psi = self.hardware_collector.collect_pod_mem_psi(
            microservices, start_time, end_time
        )
        pod_io_psi = self.hardware_collector.collect_pod_io_psi(
            microservices, start_time, end_time
        )

        return pod_mem_psi.merge(pod_cpu_psi).merge(pod_io_psi)

    def collect_jct(self) -> pd.DataFrame:
        name = self.test_case_data.name
        with open(f"{self.offline_job_output_path}/{name}", "r") as file:
            jct = float(file.readline())
        driver_jct = pd.DataFrame(
            [{"pod": "driver", "jct": jct, "task_id": 0, "node": "driver"}]
        )
        pod_jct = pd.read_csv(f"{self.offline_job_output_path}/{name}.pod_jct")
        return pd.concat([driver_jct, pod_jct])

    def collect_optum_pred_data(self):
        data = pd.DataFrame(self.optum_pred_data)
        self.optum_pred_data = []
        if len(data) == 0:
            raise RuntimeError("Got no prediction data.")
        return data

    def cache_optum_pred_data(self, data: OptumPredData):
        self.optum_pred_data.append(data)
