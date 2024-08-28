"""
Module contains the Environment Credentials File Parser class
"""
import logging

from oris.src.etc.yaml_file_loader import load_yaml_file


class EnvironmentCredentialsFileParser:
    """
    Parses the Environment Credentials file to retrieve information related to a specified
    environment and stores it in memory for future reference
    """
    def __init__(self, test_environment):
        self.test_environment = test_environment
        self.test_environment_credentials_path = 'oris/src/etc/config/env_credentials.yaml'
        self.credentials = self.__parse_environment_credentials_file__()

    def __parse_environment_credentials_file__(self):
        """
        Method to parse config/env_credentials.yaml file for a system
        """
        logging.debug(f'Opening test environment credentials file at: '
                      f'{self.test_environment_credentials_path}')
        with open(self.test_environment_credentials_path) as yaml_file_handler:
            yaml_file = load_yaml_file(yaml_file_handler, self.test_environment_credentials_path)
        if self.test_environment not in yaml_file:
            raise Exception(f'Test Environment {self.test_environment} credentials not present '
                            f'in the env_credentials file')
        test_environment_credentials = yaml_file[self.test_environment]
        logging.debug('Retrieved the following test environment credentials:')
        logging.debug(str(test_environment_credentials))
        return test_environment_credentials
