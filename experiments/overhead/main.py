from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level

# Using cgroup v1 to stop collecting PSI
# set_config_file("experiments/overhead/psi_on.yaml")
# Set /proc/sys/kernel/perf_cpu_time_max_percent to 1 to minimize CPI affects
# set_config_file("experiments/overhead/cpi_on.yaml")
set_config_file("experiments/overhead/cpi_on.yaml")
set_log_level("info")

manager.run()
