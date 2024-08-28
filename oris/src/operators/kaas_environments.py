"""
Module that contains the KaaS environment Operator
"""
import logging
import shlex
import subprocess
import os


class KaasEnvironments:
    """
    Class for the operator on KaaS Environments
    """
    def __init__(self, test_environment):
        self.test_environment = test_environment
        self.__check_if_environment_exists__()
        self.kubernetes_config_file_path = \
            f'oris/src/etc/deployment/kaas/{test_environment}/kube_config'

    def __check_if_environment_exists__(self):
        """
        Checks that we have the files for the test environment name provided
        """
        base_path = 'oris/src/etc/deployment/kaas/'
        sub_directories = os.listdir(base_path)
        if self.test_environment not in sub_directories:
            raise Exception(f'Test Environment kube config file is not present '
                            f' for \'{self.test_environment}\' environment')

    def run_command(self, command):
        """
        Executes a command
        :return: output
        :rtype: str
        """
        logging.info(f'Running the following cli command: {command}')
        try:
            command = subprocess.run(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={
                    'KUBECONFIG': self.kubernetes_config_file_path
                },
                check=True
            )
        except subprocess.CalledProcessError as grepexc:
            raise Exception(f'Error:{grepexc.output}')
        output = command.stdout.decode('utf-8').rstrip()
        return output

    def run_command_without_waiting(self, command):
        """
        Executes a command but does not wait for it to finish
        """
        logging.info(f'Running the following cli command: {command}')
        subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={
                'KUBECONFIG': self.kubernetes_config_file_path
            }
        )
