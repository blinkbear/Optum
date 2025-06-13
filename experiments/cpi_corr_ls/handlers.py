from AEFM.manager import register, manager
from AEFM import configs
from time import time
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
from AEFM.utils.prom_fetcher import PromFetcher
from AEFM.inf_generator import InfGeneratorInterface
from AEFM.inf_generator.base import BaseInfGenerator
from AEFM.models import TestCase
from AEFM.utils.logger import log
from AEFM.data_collector import TestCaseData
from AEFM.deployer.base import BaseDeployer

from ..collector import MyDataCollector, MyPromCollector


@register(event="start_experiment")
def start_experiment_handler():
    configs_obj = configs.load_configs()
    manager.data.set("configs", configs_obj)
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
    )
    manager.components.set("data_collector", data_collector)
    log.info("Generating data collector success, set to components.data_collector")
    # Deployer setup
    deployer = BaseDeployer(
        configs_obj.namespace,
        configs_obj.pod_spec,
        configs_obj.get_nodes_by_role("infra"),
        configs_obj.get_nodes_by_role("testbed"),
        configs_obj.file_paths.yaml_repo,
        configs_obj.app_img,
    )
    manager.components.set("deployer", deployer)
    log.info("Generating deployer success, set to components.deployer")
    # Interference generators setup
    inf_generators = {}
    for inf_type in configs_obj.test_cases.interferences:
        inf = configs_obj.test_cases.interferences[inf_type]
        inf_generator = BaseInfGenerator(inf_type, inf.configs)
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
    assert isinstance(configs_obj, configs.Configs)

    deployer = manager.components.get("deployer")
    assert isinstance(deployer, BaseDeployer)


@register(event="start_single_test_case")
def start_single_test_case_handler():
    test_case = manager.data.get("current_test_case")
    assert isinstance(test_case, TestCase)
    log.key(f"Current test case: {test_case}")

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


@register(event="start_data_collection")
def start_data_collection_handler():
    data_collector = manager.components.get("data_collector")
    assert isinstance(data_collector, DataCollectorInterface)
    data_collector.collect_async(manager.data.get("test_case_data"))


@register(event="end_experiment")
def end_experiment_handler():
    inf_generators = manager.components.get("inf_generators")
    for inf_types in inf_generators:
        inf_generator = inf_generators[inf_types]
        assert isinstance(inf_generator, InfGeneratorInterface)
        inf_generator.clear(wait=False)
    data_collector = manager.components.get("data_collector")
    assert isinstance(data_collector, DataCollectorInterface)
    log.info("Waiting for data collection processes finished.")
    data_collector.wait()


@register(event="start_workload")
def start_workload_handler():
    pass


@register(event="start_round")
def start_round_handler():
    deployer = manager.components.get("deployer")
    configs_obj = manager.data.get("configs")
    assert isinstance(configs_obj, configs.Configs)
    assert isinstance(deployer, BaseDeployer)

    log.info("Restaring application.")
    deployer.restart(configs_obj["app"], configs_obj["port"])
    deployer.reload(configs_obj["replicas"])
