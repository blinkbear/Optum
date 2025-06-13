from AEFM.manager import register, manager
from AEFM import configs
from time import time
from AEFM.deployer import DeployerInterface
import os
from .deployer import MyDeployer
from AEFM.workload_generator.base import (
    WrkConfig,
    BaseWorkloadGenerator,
    WorkloadGeneratorInterface,
)
from AEFM.data_collector import DataCollectorInterface
from AEFM.utils.jaeger_fetcher import JaegerFetcher
from AEFM.data_collector.jaeger_trace_collector import JaegerTraceCollector
from AEFM.data_collector.wrk_throughput_collector import (
    WrkThroughputCollector,
    WrkFetcher,
)
from AEFM.inf_generator import InfGeneratorInterface
from AEFM.inf_generator.base import BaseInfGenerator
from AEFM.models import TestCase
from AEFM.utils.logger import log
from AEFM.data_collector import TestCaseData
from AEFM.utils.prom_fetcher import PromFetcher
from ..collector import MyDataCollector, MyPromCollector
from ..offline_job import OfflineJobLauncher


@register(event="start_experiment")
def start_experiment_handler():
    configs_obj = configs.load_configs()
    manager.data.set("configs", configs_obj)
    # Deployer setup
    base_deployer = MyDeployer(
        configs_obj.namespace,
        configs_obj.pod_spec,
        configs_obj.get_nodes_by_role("infra"),
        configs_obj.get_nodes_by_role("testbed"),
        configs_obj.file_paths.yaml_repo,
        configs_obj.app_img,
    )
    manager.components.set("deployer", base_deployer)
    log.info("Generating deployer success, set to components.deployer")
    # Workload generator setup
    wrk_config = configs_obj.test_cases.workload.configs
    wrk_config = WrkConfig(
        "wrk",
        wrk_config["url"],
        wrk_config["threads"],
        wrk_config["connections"],
        configs_obj.duration,
        wrk_config["script"],
        wrk_config["rate"],
    )
    manager.components.set(
        "workload_generator",
        BaseWorkloadGenerator(wrk_config, configs_obj.file_paths["wrk_output_path"]),
    )
    log.info(
        "Generating workload generator success, set to components.workload_generator"
    )
    # Data collector setup
    jaeger_fetcher = JaegerFetcher(
        configs_obj["jaeger_host"], configs_obj["jaeger_entrance"]
    )
    jaeger_collector = JaegerTraceCollector(jaeger_fetcher)
    wrk_fetcher = WrkFetcher(configs_obj.file_paths["wrk_output_path"])
    wrk_collector = WrkThroughputCollector(wrk_fetcher)
    prom_fetcher = PromFetcher(configs_obj["prometheus_host"], configs_obj.namespace)
    prom_collector = MyPromCollector(prom_fetcher)
    data_collector = MyDataCollector(
        configs_obj.file_paths.collector_data,
        jaeger_collector,
        prom_collector,
        wrk_collector,
        configs_obj.nodes["testbed"],
        configs_obj.file_paths["offline_job_output_path"],
        collections=["min_mean_max", "node_data", "jct_data", "pod_data"],
    )
    manager.components.set("data_collector", data_collector)
    log.info("Generating data collector success, set to components.data_collector")
    offline_job_launcher = OfflineJobLauncher(
        configs_obj.file_paths["offline_job_output_path"],
        spark_path="/home/cylin/czlu_projects/understanding/bin/spark-3.5.2-bin-hadoop3/bin/spark-submit",
        hadoop_path="/home/cylin/czlu_projects/understanding/bin/hadoop-3.3.6/bin/hadoop",
        image="spark:3.5.2-java17-python3",
        k8s_master="10.119.46.42",
    )
    manager.components.set("offline_job_launcher", offline_job_launcher)
    # Interference generators setup
    inf_generators = {}
    from typing import cast, Literal

    for inf_type in configs_obj.test_cases.interferences:
        inf = configs_obj.test_cases.interferences[inf_type]
        typed_inf_type = cast(
            Literal["cpu", "mem_capacity", "mem_bandwidth", "network"], inf_type
        )
        inf_generator = BaseInfGenerator(typed_inf_type, inf.configs)
        inf_generators[inf_type] = inf_generator
    manager.components.set("inf_generators", inf_generators)
    log.info(
        "Generating interference generators success, set to components.inf_generators"
    )
    # Generate testcases
    manager.data.set("test_cases", configs_obj.test_cases)
    # Set log file location
    log.set_log_file_path(configs_obj.file_paths.log)
    log.key(f"Log file will be saved in {configs_obj.file_paths.log}.")


@register(event="init_environment")
def init_environment_handler():
    configs_obj = manager.data.get("configs")
    log.key(f"Configs: {configs_obj}")
    assert isinstance(configs_obj, configs.Configs)

    deployer = manager.components.get("deployer")
    assert isinstance(deployer, DeployerInterface)
    do_not_restart = log.countdown(
        "Skipping process: Restart application and delete all stateful microservice",
        10,
        "warn",
    )
    if not do_not_restart:
        log.info("Restaring application.")
        deployer.restart(configs_obj["app"], configs_obj["port"])
    else:
        log.info("Application restart skipped.")
    log.info("Reloading application.")
    deployer.reload(configs_obj["replicas"])


@register(event="start_single_test_case")
def start_single_test_case_handler():
    test_case = manager.data.get("current_test_case")
    assert isinstance(test_case, TestCase)
    log.key(f"Current test case: {test_case}")

    instances = test_case.additional["offline_job"]
    offline_job_launcher = manager.components.get("offline_job_launcher")
    assert isinstance(offline_job_launcher, OfflineJobLauncher)
    offline_job_launcher.start(instances, test_case.generate_name())

    workload_generator = manager.components.get("workload_generator")
    assert isinstance(workload_generator, WorkloadGeneratorInterface)
    start_time = time()
    workload_generator.run(test_case.workload.throughput, test_case.generate_name())
    end_time = time()
    test_case_data = TestCaseData(
        start_time,
        end_time,
        test_case.generate_name(),
        additional_columns=test_case.to_dict(),
    )
    manager.data.set("test_case_data", test_case_data)
    log.debug("workload generation finished", to_file=True)
    offline_job_launcher.join(test_case.generate_name())
    log.debug("offline job thread finished", to_file=True)


@register(event="start_data_collection")
def start_data_collection_handler():
    data_collector = manager.components.get("data_collector")
    assert isinstance(data_collector, DataCollectorInterface)
    data_collector.collect_async(manager.data.get("test_case_data"))


@register(event="end_experiment")
def end_experiment_handler():
    inf_generators = manager.components.get("inf_generators")
    if inf_generators is None:
        log.error("No interference generators found, skipping clearing.")
        return
    for inf_types in inf_generators:
        inf_generator = inf_generators[inf_types]
        assert isinstance(inf_generator, InfGeneratorInterface)
        inf_generator.clear(wait=False)
    data_collector = manager.components.get("data_collector")
    assert isinstance(data_collector, DataCollectorInterface)
    log.info("Waiting for data collection processes finished.")
    configs_obj = manager.data.get("configs")
    assert isinstance(configs_obj, configs.Configs)
    assignment_cmd = f"""kubectl get pod -o wide -n social | grep -v NAME | awk 'BEGIN {{print "pod,node"}} {{print $1","$7}}' > {configs_obj.file_paths.collector_data}/assignment_data.csv"""
    os.system(assignment_cmd)
    data_collector.wait()


@register(event="start_workload")
def start_workload_handler():
    pass


@register(event="start_round")
def start_round_handler():
    pass


@register(event="start_cpu")
def start_cpu_handler():
    generate_inf("cpu")


@register(event="start_mem_capacity")
def start_mem_cap_handler():
    generate_inf("mem_capacity")


@register(event="start_mem_bandwidth")
def start_mem_bandwidth_handler():
    generate_inf("mem_bandwidth")


@register(event="start_network")
def start_network_handler():
    generate_inf("network")


@register(event="start_offline_job")
def start_offline_job():
    offline_job_launcher = manager.components.get("offline_job_launcher")
    current_test_case = manager.data.get("current_test_case")
    assert isinstance(current_test_case, TestCase)
    assert isinstance(offline_job_launcher, OfflineJobLauncher)


def generate_inf(inf_type: str):
    inf_generator = manager.components.get("inf_generators")
    if inf_generator is None:
        log.error("No interference generators found, skipping generation.")
        return
    if inf_type not in inf_generator:
        log.error(f"No interference generator found for type: {inf_type}")
        return
    inf_generator = inf_generator[inf_type]
    assert isinstance(inf_generator, InfGeneratorInterface)

    current_test_case = manager.data.get("current_test_case")
    assert isinstance(current_test_case, TestCase)

    configs_obj = manager.data.get("configs")
    assert isinstance(configs_obj, configs.Configs)

    inf_count = current_test_case.interferences[inf_type]
    inf_generator.generate(
        inf_count, configs_obj.get_nodes_by_role("testbed"), wait=True
    )
