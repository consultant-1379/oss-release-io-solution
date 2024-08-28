"""
Module that contains the AWS environment Operator
"""
import logging
import shlex
import subprocess
import os


class AwsEnvironments:
    """
    Class for the operator on AWS Environments
    """
    def __init__(self, test_environment):
        self.test_environment = test_environment
        self.__check_if_environment_exists__()
        self.kubernetes_config_file_path = \
            f'oris/src/etc/deployment/aws/{test_environment}/kube_config'
        self.aws_config_path = f'oris/src/etc/deployment/aws/{test_environment}/aws_config'
        self.aws_shared_credentials_path = \
            f'oris/src/etc/deployment/aws/{test_environment}/aws_credentials'

    def __check_if_environment_exists__(self):
        """
        Checks that we have the files for the test environment name provided
        """
        base_path = 'oris/src/etc/deployment/aws/'
        sub_directories = os.listdir(base_path)
        if self.test_environment not in sub_directories:
            raise Exception(f'Test Environment config and credentials are not present '
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
                'KUBECONFIG': self.kubernetes_config_file_path,
                'AWS_CONFIG_FILE': self.aws_config_path,
                'AWS_SHARED_CREDENTIALS_FILE': self.aws_shared_credentials_path
            }
        )
