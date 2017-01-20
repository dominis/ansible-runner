from __future__ import print_function
import ansible.executor.task_queue_manager
import ansible.inventory
import ansible.parsing.dataloader
import ansible.playbook.play
import ansible.plugins.callback
import ansible.vars


class Options(object):

    def __init__(self, check=True, become=True):
        self.connection = "smart"
        self.module_path = None
        self.forks = 100
        self.remote_user = None
        self.private_key_file = None
        self.ssh_common_args = None
        self.ssh_extra_args = None
        self.sftp_extra_args = None
        self.scp_extra_args = None
        self.become = become
        self.become_method = 'sudo'
        self.become_user = 'root'
        self.verbosity = 3
        self.check = check
        super(Options, self).__init__()


class Callback(ansible.plugins.callback.CallbackBase):

    def __init__(self):
        self.unreachable = {}
        self.contacted = {}

    def runner_on_ok(self, host, result):
        self.contacted[host] = {
            "success": True,
            "result": result,
        }

    def runner_on_failed(self, host, result, ignore_errors=False):
        if ignore_errors:
            return
        self.contacted[host] = {
            "success": False,
            "result": result,
        }

    def runner_on_unreachable(self, host, result):
        self.unreachable[host] = result


class AnsibleRunnerV2(object):

    def __init__(self, host_list=None):
        self.variable_manager = ansible.vars.VariableManager()
        self.loader = ansible.parsing.dataloader.DataLoader()
        self.inventory = ansible.inventory.Inventory(
            loader=self.loader,
            variable_manager=self.variable_manager,
            host_list=host_list,
        )
        self.variable_manager.set_inventory(self.inventory)
        super(AnsibleRunnerV2, self).__init__()

    def get_hosts(self, pattern=None):
        return [
            e.name for e in self.inventory.get_hosts(pattern=pattern or "all")
        ]

    def run(
        self,
        host,
        module_name,
        module_args,
        sudo=None,
        become_pass=None,
        serial=100,
        **kwargs
    ):
        play = ansible.playbook.play.Play().load({
            "hosts": host,
            "gather_facts": "no",
            "serial": serial,
            "tasks": [{
                "action": {
                    "module": module_name,
                    "args": module_args,
                    },

            }],
        }, variable_manager=self.variable_manager, loader=self.loader)

        tqm = None
        options = Options(check=False, become=sudo)
        callback = Callback()
        try:
            tqm = ansible.executor.task_queue_manager.TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=options,
                passwords={'become_pass': become_pass},
                stdout_callback=callback,
            )
            tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()

        return callback.contacted


class AnsiblePlaybookRunnerV2(object):
    def __init__(
        self,
        target,
        playbook,
        become_pass=None,
        inventory='hosts.txt',
        logger=None,
        **kwargs
    ):
        output = []

        if isinstance(target, list):
            target = ','.join(target)

        for step in playbook:
            if not step:
                continue

            if logger:
                logger.info(
                    'ansible: host({}) module({}) params({})'
                    .format(
                        target,
                        step.get('module'),
                        step.get('params')
                    ))

            res = AnsibleRunnerV2(inventory).run(
                target,
                module_name=step.get('module'),
                module_args=step.get('params'),
                sudo=step.get('sudo', False),
                become_pass=become_pass
            )

            log = {
                '_module': step.get('module'),
                '_params': step.get('params'),
                'res': res
            }
            output.append(log)

            # Check if any of the hosts failed
            failed = [
                a for a in res.values()
                if 'failed' in a['result'].keys()
            ]
            if len(failed):
                if logger:
                    logger.debug(res)
                raise Exception(res)

        self._output = output
