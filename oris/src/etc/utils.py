"""
This module is the utility functions
"""

import json
from oris.src import configuration
from oris.src.etc import request_retry
CONSTANTS = configuration.ApplicationConfig()
DASHBOARDS_DIR_URL = CONSTANTS.get('GERRIT_URLS', 'dashboards_dir_url')
RELEASE_DASHBOARDS_DIR_URL = CONSTANTS.get('GERRIT_URLS', 'release_dashboards_dir_url')
PSO_DASHBOARDS_DIR_URL = CONSTANTS.get('GERRIT_URLS', 'pso_dashboards_dir_url')
DASHBOARDS_DIR_RUNTIME_PATH = CONSTANTS.get('FILE_PATHS', 'dashboard_dir_runtime_file')
RELEASE_DASHBOARDS_DIR_RUNTIME_PATH = CONSTANTS.get('FILE_PATHS', 'release_dashboard_dir_runtime_file')
PSO_DASHBOARDS_DIR_RUNTIME_PATH = CONSTANTS.get('FILE_PATHS', 'pso_dashboard_dir_runtime_file')
GERRIT_ORIR = CONSTANTS.get('GERRIT_URLS', 'orir')
GERRIT_PARAMETERS = ';a=blob_plain;hb=refs/heads/master;f='
GERRIT_FILE_URL = GERRIT_ORIR + GERRIT_PARAMETERS


def update_file(remote_filepath, local_filepath):
    """
    Function to update the local file with the data from the remote file
    :param remote_filepath: URL of remote file path
    :param local_filepath: the local file path where data need to be updated to
    :return: None
    """
    url = GERRIT_FILE_URL + remote_filepath
    remote_file = (request_retry.request_retry("GET", url, 5)).text
    with open(local_filepath, 'w', encoding='utf-8') as file_buf:
        file_buf.write(remote_file)


def get_list_of_files(area_type):
    """
    Function return a list of file names from the dashboard directory
    :return: file_names
    """
    if area_type == 'Release':
        remote_file = (request_retry.request_retry("GET", RELEASE_DASHBOARDS_DIR_URL, 5)).text
        with open(RELEASE_DASHBOARDS_DIR_RUNTIME_PATH, 'r+', encoding='utf-8') as file_obj:
            file_obj.write(remote_file)
        with open(RELEASE_DASHBOARDS_DIR_RUNTIME_PATH, 'r+', encoding='utf-8') as file_obj:
            file_obj.readline()
            data = file_obj.read()
            file_names = []
            json_data = json.loads(data)
            for entry in json_data["entries"]:
                file_names.append(entry["name"])
    elif area_type == 'PSO':
        remote_file = (request_retry.request_retry("GET", PSO_DASHBOARDS_DIR_URL, 5)).text
        with open(PSO_DASHBOARDS_DIR_RUNTIME_PATH, 'r+', encoding='utf-8') as file_obj:
            file_obj.write(remote_file)
        with open(PSO_DASHBOARDS_DIR_RUNTIME_PATH, 'r+', encoding='utf-8') as file_obj:
            file_obj.readline()
            data = file_obj.read()
            file_names = []
            json_data = json.loads(data)
            for entry in json_data["entries"]:
                file_names.append(entry["name"])
    else:
        remote_file = (request_retry.request_retry("GET", DASHBOARDS_DIR_URL, 5)).text
        with open(DASHBOARDS_DIR_RUNTIME_PATH, 'r+', encoding='utf-8') as file_obj:
            file_obj.write(remote_file)
        with open(DASHBOARDS_DIR_RUNTIME_PATH, 'r+', encoding='utf-8') as file_obj:
            file_obj.readline()
            data = file_obj.read()
            file_names = []
            json_data = json.loads(data)
            for entry in json_data["entries"]:
                file_names.append(entry["name"])
    return file_names
