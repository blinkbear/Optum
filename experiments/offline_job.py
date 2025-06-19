import os, threading, queue, subprocess, re, time
from AEFM.utils.files import delete_path, create_folder, write_to_file
from AEFM.utils.logger import log
from pathlib import Path
import pandas as pd


class OfflineJobLauncher:
    def __init__(
        self,
        output_path: str,
        scheduler_name: str | None = None,
        spark_path: str = "/home/cylin/czlu_projects/understanding/bin/spark-3.5.2-bin-hadoop3/bin/spark-submit",
        hadoop_path: str = "hadoop",
        image: str = "docker.io/bitnami/spark:3.5.0-debian-11-r16",
        k8s_master: str = "10.119.46.42",
    ):
        script_path = f"{Path(__file__).resolve().parent}/_spark_job.py"
        # remote_script_dir = f"hdfs://{k8s_master}:30900/python/"
        # remote_script_path = f"hdfs://{k8s_master}:30900/python/compute.py"
        # local_script_path = f"file://{script_path}"
        http_script_path = "http://10.119.46.42:5000/_spark_job.py"
        # self.hdfs_commands = (
        #     f"{hadoop_path} fs -mkdir -p {remote_script_dir};"
        #     f"{hadoop_path} fs -rm -R {remote_script_path};"
        #     f"{hadoop_path} fs -copyFromLocal {script_path} {remote_script_path}"
        # )
        self.worker_thread: None | threading.Thread = None
        self.message_queue: None | queue.Queue = None
        self.output_path = output_path
        create_folder(output_path, delete=True)
        self.run_command = (
            spark_path
            + """\
    --master k8s://https://"""
            + k8s_master
            + """:6443 \
    --deploy-mode cluster\
    --name spark-pi \
    --conf spark.executor.instances={} \
    --conf spark.kubernetes.container.image="""
            + image
            + """\
    --conf spark.kubernetes.authenticate.caCertFile=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt  \
    --conf spark.kubernetes.authenticate.oauthTokenFile=/var/run/secrets/kubernetes.io/serviceaccount/token  \
    --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
    --conf spark.kubernetes.file.upload.path=/root \
    --conf spark.kubernetes.executor.label.optum-app=pythonpi \
    --conf spark.kubernetes.executor.label.optum-type=be \
    --conf spark.executor.memory=1g \
    --conf spark.executor.memoryOverhead=1g \
    --conf spark.kubernetes.node.selector.aefm.role=testbed \
"""
        )
        if scheduler_name is not None:
            self.run_command += (
                f"--conf spark.kubernetes.executor.scheduler.name={scheduler_name} "
            )
        self.run_command += http_script_path

    def worker(self, run_command, test_case_name, message: queue.Queue):
        proc = subprocess.Popen(
            run_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )

        # Wait until: python-pi is working + available to fetch pods
        time.sleep(60)
        pod_node_file = f"{self.output_path}/{test_case_name}.pod_node"
        columns = "-o custom-columns=pod:.metadata.name,node:.spec.nodeName"
        grep = "grep -v 'driver'"
        awk = "awk '{print $1\",\"$2}'"
        command = (
            f"kubectl get pod -n default {columns} | {grep} | {awk} > '{pod_node_file}'"
        )
        os.system(command)

        stdout, stderr = proc.communicate()
        content = stdout.decode("utf-8") + stderr.decode("utf-8")
        message.put(content)

    def join(self, test_case_name: str):
        if self.worker_thread is None:
            return
        self.worker_thread.join()
        delete_path(f"{self.output_path}/{test_case_name}")
        delete_path(f"{self.output_path}/{test_case_name}.log")

        # Record the JCT provided by driver pod
        if self.message_queue is None:
            return
        message = self.message_queue.get()
        driver_pod = re.search(r"pod name:\s*(.*)\n", message)
        if driver_pod is None:
            log.warn("Get driver pod failed.", to_file=True)
            return
        driver_pod = driver_pod.group(1)
        command = f"kubectl logs -n default {driver_pod}"
        out, _ = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE
        ).communicate()
        logs = out.decode("utf-8")
        jct = re.search(r"Job 0 finished.*\s(\d+\.\d+)\ss\n", logs)
        if jct is None:
            log.warn("Get driver jct failed.", to_file=True)
            return
        jct = jct.group(1)
        if jct is None:
            print("jct is None")
            return
        else:
            print("jct is ", jct)
        write_to_file(f"{self.output_path}/{test_case_name}", f"{jct}\n")
        write_to_file(f"{self.output_path}/{test_case_name}.log", f"{message}\n")

        # Record the JCT of each task on each executor
        pod_jct_csv = []
        for line in logs.split("\n"):
            pod_jct = re.search(
                r"Finished task .* \(TID (\d+)\) in (\d+) ms on .* \(executor (\d+)\)",
                line,
            )
            if pod_jct is not None:
                task_id, jct, executor = pod_jct.groups()
                pod_jct_csv.append(
                    {"task_id": task_id, "executor": executor, "jct": jct}
                )
        pod_jct_csv = pd.DataFrame(pod_jct_csv)

        # Get node that the pod assigned to.
        pod_node_file = f"{self.output_path}/{test_case_name}.pod_node"
        pod_jct_file = f"{self.output_path}/{test_case_name}.pod_jct"
        pod_node_csv = pd.read_csv(pod_node_file)
        pod_node_csv = pod_node_csv.assign(
            executor=pod_node_csv["pod"].apply(lambda x: str(x).split("-")[-1])
        )

        pod_jct_csv.merge(pod_node_csv).drop(columns="executor").to_csv(
            pod_jct_file, index=False
        )

    def start(self, instances, test_case_name):
        # os.system(self.hdfs_commands)
        run_command = self.run_command.format(str(instances))
        message = queue.Queue()
        worker_thread = threading.Thread(
            target=self.worker, args=(run_command, test_case_name, message)
        )
        worker_thread.start()
        self.worker_thread = worker_thread
        self.message_queue = message
