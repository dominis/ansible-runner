from __future__ import print_function
import logging
from ansiblerunner import AnsiblePlaybookRunnerV2

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%I-%d %H:%M:%S'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


become_pass = None # sudo pass
target = 'vfappd001.mgt.dmc-int.net'

playbook = [
    {
        'module': 'shell',
        'params': 'df -h',
        'sudo': False
    }
]

res = AnsiblePlaybookRunnerV2(
    target=target,
    playbook=playbook,
    become_pass=become_pass,
    logger=logger
)

print(res._output)
