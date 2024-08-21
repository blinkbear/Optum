from AEFM.deployer.base import BaseDeployer
from AEFM.utils.kubernetes import delete_by_yaml, deploy_by_yaml
from AEFM.utils.files import delete_path, create_folder
from AEFM.utils.kubernetes_YAMLs import KubernetesYAMLs


class MyDeployer(BaseDeployer):

    def deploy_infra_yaml(self) -> BaseDeployer:
        delete_by_yaml(self.tmp_infra_path, wait=True, namespace=self.namespace)
        deploy_by_yaml(self.tmp_infra_path, wait=True, namespace=self.namespace)
        return self

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
        ).assign_affinity(self.testbed_nodes).assign_containers(replicas).update(
            "spec.template.spec.containers[0].imagePullPolicy", "IfNotPresent"
        ).update(
            "spec.template.spec.containers[0].env",
            [
                {"name": "JAEGER_SAMPLE_PARAM", "value": "1"},
                {"name": "JAEGER_SAMPLE_TYPE", "value": "ratelimiting"},
            ],
        ).save(
            self.tmp_under_test_path
        )
        return self
