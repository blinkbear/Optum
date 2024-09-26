from AEFM.data_collector.jaeger_trace_collector import JaegerTraceCollector
from AEFM.data_collector.models import CpuUsage, MemUsage
from AEFM.data_collector.wrk_throughput_collector import WrkThroughputCollector
import pandas as pd
from AEFM.data_collector.base import BaseDataCollector, Collection
from AEFM.utils.logger import log
from AEFM.data_collector.prom_hardware_collector import PromHardwareCollector
from AEFM.models import Node
from statistics import mean


class MyPromCollector(PromHardwareCollector):
    def collect_node_cpu(self, nodes: list[Node], start_time, end_time):
        ips = [node.ip for node in nodes]
        constraint = ":9100|".join(ips) + ":9100"
        query = f'instance:node_cpu_utilisation:rate5m{{instance=~"{constraint}"}}'
        response = self.fetcher.fetch(query, "range", 1, start_time, end_time)
        log.debug(
            f"{__file__}: Fetch Node CPU usage from: {response.url}", to_file=True
        )
        usage = response.json()
        records = []
        if usage["data"] and usage["data"]["result"]:
            for data in usage["data"]["result"]:
                ip = str(data["metric"]["instance"]).split(":")[0]
                usage = max([float(v[1]) for v in data["values"]])
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

        node_data = Collection(
            "node data",
            f"{self.data_path}/node_data.csv",
            self.collect_node,
        )
        jct_data = Collection(
            "JCT data", f"{self.data_path}/jct_data.csv", self.collect_jct
        )
        self.add_new_collections([node_data, jct_data])

    def collect_node(self) -> pd.DataFrame:
        start_time = self.test_case_data.start_time
        end_time = self.test_case_data.end_time
        assert isinstance(self.hardware_collector, MyPromCollector)

        cpu = self.hardware_collector.collect_node_cpu(self.nodes, start_time, end_time)
        mcp = self.hardware_collector.collect_node_mcp(self.nodes, start_time, end_time)
        net = self.hardware_collector.collect_node_net(self.nodes, start_time, end_time)
        psi = self.hardware_collector.collect_node_psi(self.nodes, start_time, end_time)
        # Stop collecting CPI since heavy overhead
        # cpi = self.hardware_collector.collect_node_cpi(self.nodes, start_time, end_time)
        # return cpu.merge(mcp).merge(net).merge(psi).merge(cpi)
        return cpu.merge(mcp).merge(net).merge(psi)

    # def collect_hardware(self) -> pd.DataFrame:
    #     start_time = self.test_case_data.start_time
    #     end_time = self.test_case_data.end_time
    #     assert isinstance(self.hardware_collector, MyPromCollector)

    #     hardware_data = super().collect_hardware()
    #     pod_cpi = self.hardware_collector.collect_pod_cpi(start_time, end_time)

    #     microservices = self.statistical_data["microservice"].dropna().unique().tolist()
    #     pod_cpu_psi = self.hardware_collector.collect_pod_cpu_psi(
    #         microservices, start_time, end_time
    #     )
    #     pod_mem_psi = self.hardware_collector.collect_pod_mem_psi(
    #         microservices, start_time, end_time
    #     )
    #     pod_io_psi = self.hardware_collector.collect_pod_io_psi(
    #         microservices, start_time, end_time
    #     )

    #     return (
    #         hardware_data.merge(pod_mem_psi)
    #         .merge(pod_cpu_psi)
    #         .merge(pod_io_psi)
    #         .merge(pod_cpi, how="left")
    #     )

    def collect_jct(self) -> pd.DataFrame:
        name = self.test_case_data.name
        with open(f"{self.offline_job_output_path}/{name}", "r") as file:
            jct = float(file.readline())
        driver_jct = pd.DataFrame(
            [{"pod": "driver", "jct": jct, "task_id": 0, "node": "driver"}]
        )
        pod_jct = pd.read_csv(f"{self.offline_job_output_path}/{name}.pod_jct")
        return pd.concat([driver_jct, pod_jct])
