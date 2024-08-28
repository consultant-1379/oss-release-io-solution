"""
Contains methods related to loading YAML files
"""
import logging
import yaml


def load_yaml_file(file_handle, file_path):
    """
    Returns content of a yaml file as dict
    :param file_handle: file handle pointing to the file the user wants to read from
    :param file_path:
    :return: contents of the yaml file as dict
    :rtype: dict
    """
    try:
        return yaml.safe_load(file_handle)
    except yaml.YAMLError as exception:
        logging.error(f'Failed to load file: {file_path}')
        logging.error(str(exception))
        raise
