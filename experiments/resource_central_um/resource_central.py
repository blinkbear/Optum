from AEFM.deployer.base import BaseDeployer
from AEFM.models import Node, PodSpec
from AEFM.utils.files import delete_path, create_folder
from AEFM.utils.kubernetes import delete_by_yaml, deploy_by_yaml, wait_deployment
from AEFM.utils.kubernetes_YAMLs import KubernetesYAMLs
from scheduler.baselines import RESOURCE_CENTRAL_NAME, ResourceCentralScheduler


class ResourceCentralDeployer(BaseDeployer):
    def __init__(
        self,
        namespace: str,
        pod_spec: PodSpec,
        infra_nodes: list[Node],
        testbed_nodes: list[Node],
        yaml_repo: str,
        scheduler: ResourceCentralScheduler,
        app_img: str | None = None,
    ):
        super().__init__(
            namespace, pod_spec, infra_nodes, testbed_nodes, yaml_repo, app_img
        )
        self.scheduler = scheduler

    def prepare_under_test_yaml(
        self, replicas: dict[str, int] | None = None
    ) -> BaseDeployer:
        replicas = replicas if replicas is not None else {}
        # Clear YAML files generated previously
        delete_path(self.tmp_under_test_path)
        create_folder(self.tmp_under_test_path)
        # Edit under_test YAMLs, save them to tmp folder
        under_test = KubernetesYAMLs(f"{self.yaml_repo}/under_test")
        under_test.base_yaml_preparation(
            self.namespace, self.pod_spec, self.app_img
        ).assign_containers(replicas).update(
            "spec.template.spec.containers[0].imagePullPolicy", "IfNotPresent"
        ).update(
            "spec.template.spec.schedulerName", RESOURCE_CENTRAL_NAME
        ).update(
            "spec.template.spec.containers[0].env",
            [
                {"name": "JAEGER_SAMPLE_PARAM", "value": "1"},
                {"name": "JAEGER_SAMPLE_TYPE", "value": "ratelimiting"},
                {"name": "MY_NAMESPACE", "valueFrom": {"fieldRef": {"fieldPath": "metadata.namespace"}}},
            ],
        ).save(
            self.tmp_under_test_path
        )
        return self

    def deploy_under_test_yaml(self) -> BaseDeployer:
        delete_by_yaml(self.tmp_under_test_path, wait=True, namespace=self.namespace)
        deploy_by_yaml(self.tmp_under_test_path)
        return self

    def reload(self, replicas: dict[str, int], online_qps: float):
        self.scheduler.set_qps(online_qps)
        self.prepare_under_test_yaml(replicas).deploy_under_test_yaml()
        wait_deployment(self.namespace, 300)
