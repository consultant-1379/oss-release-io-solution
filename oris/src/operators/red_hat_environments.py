"""
Module that contains the Red Hat Environments Operator
"""

from oris.src.operators.environment_details_parser import EnvironmentCredentialsFileParser
from oris.src.operators.ssh_shell import SshShell


class RedHatEnvironments:
    """
    Class for the operator on Red Hat Environments
    """
    def __init__(self, test_environment):
        self.environment_details = EnvironmentCredentialsFileParser(test_environment)
        self.ssh_shell = SshShell(
            target_host=self.environment_details.credentials['IP'],
            user=self.environment_details.credentials['SSH_USER'],
            pem_file=self.environment_details.credentials['SSH_PEM_FILE'],
        )
        self.ccd_director_ip = self.environment_details.credentials['IP']
