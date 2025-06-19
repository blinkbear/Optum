from .handlers import *
from AEFM.manager import manager
from AEFM import set_config_file, set_log_level
import os

set_config_file("experiments/profiling_sn_um/profiling.yaml")
set_log_level("info")

manager.run()
os.system("""kubectl get pod -o wide -n social | grep -v NAME |
    awk 'BEGIN {print "pod,node"} {print $1","$7}' > experiments/profiling_sn_um/assignment_data.csv""")
