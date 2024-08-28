"""
Module contains the kubectl helper class
"""
import logging

from oris.src.operators.kaas_environments import KaasEnvironments
from oris.src.operators.red_hat_environments import RedHatEnvironments
from oris.src.operators.aws_environments import AwsEnvironments
from oris.src.operators.azure_environments import AzureEnvironments
from oris.src.operators.cnis_environments import CnisEnvironments
from oris.src.operators.ocp_environments import OcpEnvironments


class KubectlHelper:
    """
    Helps run kubectl by providing a wrapper around the functionality that changes how we run
    kubectl commands based on what platform we are running against.
    """
    def __init__(self, test_environment, platform_type):
        self.test_environment = test_environment
        self.platform_type = platform_type
        self.kube_config_default_location = '/root/.kube/config'
        self.__setup_kubectl_helper__()

    def run_command(self, command, output_to_screen=True):
        """
        Runs a command against a Kubernetes environment
        :param command:
        :param output_to_screen:
        :return: command output
        :rtype: string
        """
        if self.platform_type == 'RH':
            command_output = self.red_hat_environments.ssh_shell.run_command(command)
        elif self.platform_type == 'AWS':
            command_output = self.aws_environments.run_command(command)
        elif self.platform_type == 'KaaS':
            command_output = self.kaas_environments.run_command(command)
        elif self.platform_type == 'Azure':
            command_output = self.azure_environments.run_command(command)
        elif self.platform_type == 'CNIS':
            command_output = self.cnis_environments.run_command(command)
        elif self.platform_type == 'OCP':
            command_output = self.ocp_environments.run_command(command)
        else:
            raise Exception('Platform type not supported yet')
        if output_to_screen:
            logging.info("Command output: \n" + command_output)
        return command_output

    def run_command_without_waiting(self, command):
        """
        Runs a command against a Kubernetes environment without waiting for it to finish
        :param command:
        """
        if self.platform_type == 'RH':
            self.red_hat_environments.ssh_shell.run_command(command)
        elif self.platform_type == 'AWS':
            self.aws_environments.run_command_without_waiting(command)
        elif self.platform_type == 'KaaS':
            self.kaas_environments.run_command_without_waiting(command)
        elif self.platform_type == 'Azure':
            self.azure_environments.run_command_without_waiting(command)
        elif self.platform_type == 'CNIS':
            self.cnis_environments.run_command_without_waiting(command)
        elif self.platform_type == 'OCP':
            self.ocp_environments.run_command_without_waiting(command)
        else:
            raise Exception('Platform type not supported yet')

    def __setup_kubectl_helper__(self):
        """
        Sets up the Kubectl Helper depending on what platform type was provided
        """
        if self.platform_type == 'RH':
            self.red_hat_environments = RedHatEnvironments(self.test_environment)
        elif self.platform_type == 'AWS':
            self.aws_environments = AwsEnvironments(self.test_environment)
        elif self.platform_type == 'KaaS':
            self.kaas_environments = KaasEnvironments(self.test_environment)
        elif self.platform_type == 'Azure':
            self.azure_environments = AzureEnvironments(self.test_environment)
        elif self.platform_type == 'CNIS':
            self.cnis_environments = CnisEnvironments(self.test_environment)
        elif self.platform_type == 'OCP':
            self.ocp_environments = OcpEnvironments(self.test_environment)
        else:
            raise Exception('Platform type not supported yet')
