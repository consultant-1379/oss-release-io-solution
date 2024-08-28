"""
Module contains the Grafana and Prometheus Setup class
"""

from urllib.parse import urlsplit

from base64 import b64decode
import logging
import time
import os
import json
import fnmatch
import re
import yaml
import requests

from oris.src.etc.yaml_file_loader import load_yaml_file
from oris.src.etc import utils
from oris.src import configuration
from oris.src.operators.aws_environments import AwsEnvironments
from oris.src.operators.environment_details_parser import EnvironmentCredentialsFileParser
from oris.src.operators.kaas_environments import KaasEnvironments
from oris.src.operators.sftp_server_connection import SFTPServerConnection
from oris.src.operators.kubectl_helper import KubectlHelper
from oris.src.operators.red_hat_environments import RedHatEnvironments
from oris.src.operators.azure_environments import AzureEnvironments
from oris.src.operators.cnis_environments import CnisEnvironments
from oris.src.operators.ocp_environments import OcpEnvironments
from oris.src.etc.request_retry import request_retry
CONSTANTS = configuration.ApplicationConfig()


# pylint: disable=too-many-instance-attributes
class GrafanaPrometheusSetup:
    """
    Helps run Grafana and Prometheus Setup
    """

    def __init__(self, test_environment_name, platform_type, area_type):
        self.kubectl_helper = KubectlHelper(test_environment_name, platform_type)
        self.platform_type = platform_type
        self.test_environment_name = test_environment_name
        self.area_type = area_type
        self.grafana_password = None
        self.grafana_url = None
        self.prometheus_url = None
        self.prometheus_monitoring_url = None
        self.prometheus_namespace = None
        self.service_url = None
        self.grafana_user = 'admin'
        self.custom_grafana_password = 'passw0rd'
        self.grafana_namespace = None
        self.grafana_repo_name = 'grafana'
        self.grafana_prometheus_config_files_path = 'oris/src/etc/config/grafana_prometheus_configs'
        self.namespaces_to_delete = ['monitoring']
        self.service_to_get_virtualservice_of = 'eric-oss-common-base-gas-virtualservice'
        self.dockerhub_url = 'armdocker.rnd.ericsson.se/dockerhub-ericsson-remote'
        self.__get_prometheus_namespace__()
        self.__set_grafana_namespace__()
        self.__set_service_url__()
        self.__set_prometheus_url__()
        self.__set_prometheus_monitoring_url__()
        self.__set_grafana_url__()
        self.platform_operator = self.__get_platform_operator__()

    def __get_platform_operator__(self):
        """
        Gets the correct platform operator based on platform type provided
        """
        if self.platform_type == 'RH':
            return RedHatEnvironments(self.test_environment_name)
        if self.platform_type == 'AWS':
            return AwsEnvironments(self.test_environment_name)
        if self.platform_type == 'KaaS':
            return KaasEnvironments(self.test_environment_name)
        if self.platform_type == 'Azure':
            return AzureEnvironments(self.test_environment_name)
        if self.platform_type == 'CNIS':
            return CnisEnvironments(self.test_environment_name)
        if self.platform_type == 'OCP':
            return OcpEnvironments(self.test_environment_name)
        raise Exception('Bad move Thunderbee. Make sure to code up the platform type you are '
                        'working on!')

    def __set_service_url__(self):
        """
        This sets the common section of environments URL
        Regardless of whether we are setting up grafana or prometheus, they both have common sections
        of their URLs
        We get these URLs from the Virtual service from a service on the environment
        """
        get_service_virtualservice_information_cmd = f'/usr/local/bin/kubectl get virtualservice ' \
                                                     f'{self.service_to_get_virtualservice_of} '  \
                                                     f'-n {self.prometheus_namespace} --no-headers'
        try:
            get_service_virtualservice_information_output = \
                self.kubectl_helper.run_command(get_service_virtualservice_information_cmd, False)
        except ConnectionError:
            raise Exception("Virtual service is not available")

        broken_down_line = get_service_virtualservice_information_output.split()
        if len(broken_down_line) < 3:
            raise Exception('Invalid output detected when getting prometheus URL. '
                            'Please check above.')
        index_of_service_url = [idx for idx, s in enumerate(broken_down_line) if '.ericsson.se' in s][0]
        self.service_url = broken_down_line[index_of_service_url][broken_down_line[
            index_of_service_url].index('.') + 1:]
        self.service_url = self.service_url[0:-2]
        if get_service_virtualservice_information_output is None:
            logging.info("No Virtual service")
        if not self.service_url:
            raise Exception('Unable to determine URL to use for services')

    def __get_environment_name_from_kubeconfig__(self):
        """
        Gets the environments cluster name from the kubeconfig file
        """
        get_environment_name_from_kubeconfig_cmd = "/usr/local/bin/kubectl config view " \
                                                   "-o jsonpath='{.clusters[0].name}'"
        return self.kubectl_helper.run_command(
            get_environment_name_from_kubeconfig_cmd, False)

    def __get_prometheus_namespace__(self):
        """"
        Executes command to get the prometheus namespace
        """
        get_prometheus_namespace_cmd = '/usr/local/bin/kubectl get pods -A -l ' \
                                       'app=eric-pm-server -o jsonpath="{.items[*].metadata.namespace}"'
        get_prometheus_namespace_output = self.kubectl_helper.run_command(get_prometheus_namespace_cmd, False)
        if get_prometheus_namespace_output:
            if self.platform_type == 'RH':
                get_user_command = 'whoami'
                cmd_output = self.kubectl_helper.run_command(get_user_command, True)
                user = cmd_output.splitlines()[0]
                command_to_array = get_prometheus_namespace_output.splitlines()
                namespace_values = []
                for value in command_to_array:
                    if '/usr/local/bin/kubectl' not in value and 'echo end of stdOUT buffer.' not in value:
                        namespace_values.append(value)
                namespace_values = str(namespace_values[0]).split(user)[0].split(' ')
                valid_namespace = []
                for namespace in namespace_values:
                    if namespace not in self.namespaces_to_delete:
                        valid_namespace.append(namespace)
                self.prometheus_namespace = valid_namespace[0]
            elif self.platform_type == 'CNIS':
                namespaces_returned = get_prometheus_namespace_output.split()
                for namespace in namespaces_returned:
                    if namespace.__contains__('oss-deploy') and self.test_environment_name[-1].lower() == namespace[-1]:
                        self.prometheus_namespace = namespace
            elif self.platform_type == 'Azure':
                namespaces_returned = get_prometheus_namespace_output.split()
                for namespace in namespaces_returned:
                    if namespace not in ['default', 'monitoring']:
                        self.prometheus_namespace = namespace
            elif self.platform_type == 'KaaS':
                namespaces_returned = get_prometheus_namespace_output.split()
                for namespace in namespaces_returned:
                    if namespace not in ['default', 'appstaging-monitoring']:
                        self.prometheus_namespace = namespace
            else:
                self.prometheus_namespace = get_prometheus_namespace_output
        logging.info(f'Prometheus namespace: {self.prometheus_namespace}')
        if self.prometheus_namespace is None:
            raise Exception("Ensure eric-pm-server is available")

    def __set_grafana_namespace__(self):
        """
        Sets Grafana namespace based on EIAP namespace
        """
        if not self.prometheus_namespace:
            raise Exception('No service url set and therefore unable to set prometheus URL')
        self.grafana_namespace = f'grafana-{self.prometheus_namespace}'
        logging.info(f'Grafana Namespace: {self.grafana_namespace}')

    def __set_prometheus_url__(self):
        """"
        Executes command to set the prometheus url
        """
        if not self.service_url:
            raise Exception('No service url set and therefore unable to set prometheus URL')
        if self.platform_type == "AWS":
            self.prometheus_url = f'https://prometheus-{self.prometheus_namespace}.{self.service_url}/metrics/viewer'
        else:
            self.prometheus_url = f'http://prometheus-{self.prometheus_namespace}.{self.service_url}/metrics/viewer'
        logging.info(f'Prometheus URL: {self.prometheus_url}')

    def __set_prometheus_monitoring_url__(self):
        """"
        Executes command to set the monitoring namespace prometheus url
        """
        if not self.service_url:
            raise Exception('No service url set and therefore unable to set prometheus URL for montioring namespace')
        if self.platform_type == "AWS":
            self.prometheus_monitoring_url = \
                f'https://prometheus-monitoring-{self.prometheus_namespace}.{self.service_url}'
        else:
            self.prometheus_monitoring_url = \
                f'http://prometheus-monitoring-{self.prometheus_namespace}.{self.service_url}'
        logging.info(f'Prometheus URL: {self.prometheus_monitoring_url}')

    def __set_grafana_url__(self):
        """
        Executes command to set the grafana url
        """
        if not self.service_url:
            raise Exception('No service url set and therefore unable to set Grafana URL')
        if self.platform_type == "AWS":
            self.grafana_url = f'https://{self.grafana_namespace}.{self.service_url}'
        else:
            self.grafana_url = f'http://{self.grafana_namespace}.{self.service_url}'
        logging.info(f'Grafana URL: {self.grafana_url}')

    def __get_pod_names_in_namespace__(self, namespace):
        """"
        Executes command to get the pods in a namespace
        :param: namespace
        :return: kubectl get pods command output
        :rtype: str
        """
        get_pods_cmd = f'/usr/local/bin/kubectl get pods -n {namespace} -o name'
        get_pods_output = self.kubectl_helper.run_command(get_pods_cmd, False)
        return get_pods_output

    def determine_if_namespace_needs_to_be_cleared(self):
        """
        Executes logic to try and see if we have access to a running grafana instance
        If we have access, do nothing. If we don't have access which is a common issue,
        delete the grafana namespace
        """
        if self.platform_type in ['Azure', 'KaaS', 'RH', 'CNIS', 'OCP']:
            logging.info('Checking if grafana namespace needs to be cleaned up.')
            get_namespace_cmd = f'/usr/local/bin/kubectl get ns {self.grafana_namespace} -o name'
            if self.kubectl_helper.run_command(get_namespace_cmd):
                logging.info('Namespace already Exist! Hence cleaning up the namespace.')
                delete_grafana_namespace_cmd = \
                    f'/usr/local/bin/kubectl delete namespace {self.grafana_namespace}'
                self.kubectl_helper.run_command(delete_grafana_namespace_cmd)
                logging.info("Grafana namespace deleted")
            else:
                logging.info("There is no namespace available. New namespace need to be created")

    def __create_grafana_namespace__(self):
        """"
        Executes command to create namespace
        """
        create_namespace_cmd = f'/usr/local/bin/kubectl create namespace {self.grafana_namespace}'
        self.kubectl_helper.run_command(create_namespace_cmd)

    def __add_and_update_helmchart_repo__(self):
        """"
        Executes commands to add and update grafana helm-chart repository
        """
        helm_add_cmd = \
            f"/usr/local/bin/helm repo add {self.grafana_repo_name} https://grafana.github.io/helm-charts"
        self.kubectl_helper.run_command(helm_add_cmd)

        helm_update_cmd = '/usr/local/bin/helm repo update'
        self.kubectl_helper.run_command(helm_update_cmd)

    def __create_pod__(self):
        """"
        Executes commands to helm install pod and waits to ensure POD is Running
        """
        helm_install_cmd = f"/usr/local/bin/helm install {self.grafana_namespace} " \
                           f"grafana/grafana -n {self.grafana_namespace} --set " \
                           f"image.repository={self.dockerhub_url}/grafana/grafana"
        self.kubectl_helper.run_command(helm_install_cmd, False)
        self.__verify_grafana_pod_created__(20)

    def __verify_grafana_pod_created__(self, max_retry):
        count = 0
        while count < max_retry:
            logging.info("Sleeping for 10 seconds to make sure grafana POD is running")
            time.sleep(10)
            get_pod_cmd = f"/usr/local/bin/kubectl get pods --namespace {self.grafana_namespace} " \
                          f"--field-selector=status.phase=Running --no-headers"
            get_running_pod_output = self.kubectl_helper.run_command(get_pod_cmd, False)
            if get_running_pod_output and 'No resources found' not in get_running_pod_output:
                break
            count += 1
            if count == max_retry:
                raise Exception('Grafana POD was not set to a Running in the required time frame')

    def __get_grafana_password__(self):
        """"
        Executes commands to get the grafana password
        """
        get_grafana_password_cmd = \
            f'/usr/local/bin/kubectl get secret --namespace {self.grafana_namespace} {self.grafana_namespace} ' \
            '-o jsonpath="{.data.admin-password}"'
        grafana_secret = self.kubectl_helper.run_command(get_grafana_password_cmd).strip()

        logging.debug(f"Grafana secret is: {grafana_secret}")
        self.grafana_password = b64decode(grafana_secret).decode()
        logging.info(f"Original Grafana password is: {self.grafana_password}")

    def set_custom_grafana_password(self):
        """"
        Executes command to set the grafana custom password
        """
        logging.info('Setting the custom Grafana password')
        request_body = {
            'oldPassword': self.grafana_password,
            'newPassword': self.custom_grafana_password,
            'confirmNew': self.custom_grafana_password
        }
        logging.info(f'Request body: {request_body}')

        target_url = f'{self.grafana_url}/api/user/password'
        logging.debug(f'Target URL: {target_url}')

        update_grafana_password_response = \
            request_retry("PUT", target_url, 5, body=request_body,
                          auth=(self.grafana_user, self.grafana_password), ssl=True)

        logging.info(f'Response details: {update_grafana_password_response.text}')

        if not update_grafana_password_response.ok:
            raise Exception('Something went wrong in updating Grafana password')

        self.grafana_password = self.custom_grafana_password
        logging.info('Grafana password updated successfully!')
        logging.info(f'New Grafana password: {self.grafana_password}')

    def __get_pod_name__(self):
        """
        Executes command to get pod name
        :return: pod_name
        :rtype: str
        """
        get_pods_cmd = f'/usr/local/bin/kubectl get pods --namespace {self.grafana_namespace} ' \
                       '--field-selector=status.phase=Running -l ' \
                       'app.kubernetes.io/name=grafana ' \
                       '--output=jsonpath={.items..metadata.name}'

        pod_command_output = self.kubectl_helper.run_command(get_pods_cmd, True)
        if self.platform_type == 'RH':
            pod_name = self.__extract_pod_name__(pod_command_output)
        else:
            pod_name = pod_command_output.split('\n', maxsplit=1)[0].strip()
        logging.info(f"Pod name is: {pod_name}")
        return pod_name

    @staticmethod
    def __extract_pod_name__(command_output):
        try:
            command_to_array = command_output.splitlines()
            for value in command_to_array:
                if re.match('grafana-', value):
                    return value[0:24]
            raise Exception('No Pod found!')
        except Exception:
            logging.error('Issue in getting the Pod name.')
            raise

    def __set_port_forwarding_for_pod__(self, pod_name):
        """"
        Executes command to set port forwarding for the grafana pod in the grafana namespace
        :param pod_name:
        """
        if self.platform_type == 'RH':
            port_forwarding_cmd = f'/usr/local/bin/kubectl --namespace {self.grafana_namespace} ' \
                              f'port-forward {pod_name} 3000 &'
        else:
            port_forwarding_cmd = f'/usr/local/bin/kubectl --namespace {self.grafana_namespace} ' \
                              f'port-forward {pod_name} 3000'
        self.kubectl_helper.run_command_without_waiting(port_forwarding_cmd)

    def install_grafana(self):
        """
        If necessary it creates Grafana namespace, Helm installs Grafana and creates the Grafana pod
        Then it port forwards namespace on port 3000 and applies Grafana gateway, virtual service and
        service entry on same namespace as EIAP.
        """
        logging.info('Installing Grafana')
        try:
            self.__create_grafana_namespace__()
            self.__add_and_update_helmchart_repo__()
            self.__create_pod__()
            logging.info('Grafana Namespace and Pod created successfully')
            self.__get_grafana_password__()
            grafana_pod_name = self.__get_pod_name__()
            self.__set_port_forwarding_for_pod__(grafana_pod_name)

            logging.info('Grafana Install executed successfully')

        except Exception:
            logging.error('Grafana Install failed')
            raise

    def __update_hostname_in_rs_file__(self, hostname, svc_fdqn, rs_file_path):
        """
        Updates the resources file with the Grafana hostname.
        :param hostname:
        :param rs_file_path:
        """
        logging.info(f'Updating Hostname in {rs_file_path}')

        logging.info(f'Reading in {rs_file_path} file')
        with open(rs_file_path, 'r', encoding='utf-8') as yaml_file:
            yaml_content = load_yaml_file(yaml_file, rs_file_path)
            if 'gateway' in rs_file_path:
                yaml_content['spec']['servers'][0]['hosts'][0] = f'{hostname}'
            elif 'virtualservice' in rs_file_path:
                yaml_content['spec']['hosts'][0] = f'{hostname}'
                yaml_content['spec']['http'][0]['route'][0]['destination']['host'] = f'{svc_fdqn}'
            elif 'serviceentry' in rs_file_path:
                yaml_content['spec']['hosts'][0] = f'{svc_fdqn}'
            else:
                raise Exception('Resource type not supported yet')

        logging.info(f'Writing updated YAML contents to {rs_file_path} file')
        with open(rs_file_path, 'w', encoding='utf-8') as yaml_file:
            yaml.dump(yaml_content, yaml_file, default_flow_style=False)

    def configure_grafana(self):
        """
        Edits resources files to have correct Grafana URL
        Uploads grafana-gateway.yaml, grafana-virtualservice and grafana-serviceentry.yaml to the Grafana instance
        """
        logging.info('Configuring Grafana')
        try:
            grafana_hostname = urlsplit(self.grafana_url).hostname
            svc_fqdn = f'{self.grafana_namespace}.{self.grafana_namespace}.svc.cluster.local'
            logging.info(f'Grafana Hostname: {grafana_hostname}')
            gw_file_path = \
                f'{self.grafana_prometheus_config_files_path}/grafana-gateway.yaml'
            self.__update_hostname_in_rs_file__(grafana_hostname, svc_fqdn, gw_file_path)

            vs_file_path = \
                f'{self.grafana_prometheus_config_files_path}/grafana-virtualservice.yaml'
            self.__update_hostname_in_rs_file__(grafana_hostname, svc_fqdn, vs_file_path)

            se_file_path = \
                f'{self.grafana_prometheus_config_files_path}/grafana-serviceentry.yaml'
            self.__update_hostname_in_rs_file__(grafana_hostname, svc_fqdn, se_file_path)

            grafana_config_files = \
                ['grafana-gateway.yaml', 'grafana-virtualservice.yaml', 'grafana-serviceentry.yaml']
            self.__upload_files_from_local_to_ccd__(grafana_config_files)

            grafana_prometheus_config_files_directory = \
                self.__get_grafana_prometheus_config_files_directory__()

            kubectl_apply_gw_cmd = \
                f'/usr/local/bin/kubectl apply -f ' \
                f'{grafana_prometheus_config_files_directory}/grafana-gateway.yaml ' \
                f'-n {self.prometheus_namespace}'
            self.kubectl_helper.run_command(kubectl_apply_gw_cmd)

            kubectl_apply_vs_cmd = \
                f'/usr/local/bin/kubectl apply -f ' \
                f'{grafana_prometheus_config_files_directory}/grafana-virtualservice.yaml ' \
                f'-n {self.prometheus_namespace}'
            self.kubectl_helper.run_command(kubectl_apply_vs_cmd)

            kubectl_apply_se_cmd = \
                f'/usr/local/bin/kubectl apply -f ' \
                f'{grafana_prometheus_config_files_directory}/grafana-serviceentry.yaml ' \
                f'-n {self.prometheus_namespace}'
            self.kubectl_helper.run_command(kubectl_apply_se_cmd)

            logging.info('Grafana configuration executed successfully')

        except Exception as exception:
            logging.error(f'Grafana configuration failed, Exception: {exception}')

    def __get_grafana_prometheus_config_files_directory__(self):
        """
        Gets the appropriate config files directory based on platform type
        :return: config_files_directory
        :rtype: str
        """
        if self.platform_type == 'RH':
            return '/tmp'
        return 'oris/src/etc/config/grafana_prometheus_configs'

    def prometheus_setup(self):
        """
        Updates prometheus gateway, virtual service with hostname, applies prometheus gateway
        and prometheus virtual service, and uploads them to ccd.
        """
        try:
            svc_fqdn = f'eric-pm-server.{self.prometheus_namespace}.svc.cluster.local'
            prometheus_hostname = urlsplit(self.prometheus_url).hostname
            logging.info(f'Prometheus Hostname: {prometheus_hostname}')

            prometheus_gateway_file = os.path.join(self.grafana_prometheus_config_files_path,
                                                   "prometheus-gateway.yaml")
            self.__update_hostname_in_rs_file__(prometheus_hostname, svc_fqdn, prometheus_gateway_file)

            prometheus_virtualservice_file = os.path.join(self.grafana_prometheus_config_files_path,
                                                          "prometheus-virtualservice.yaml")
            self.__update_hostname_in_rs_file__(prometheus_hostname, svc_fqdn, prometheus_virtualservice_file)

            prometheus_config_files = \
                ['prometheus-gateway.yaml', 'prometheus-virtualservice.yaml']

            self.__upload_files_from_local_to_ccd__(prometheus_config_files)

            self.__apply_prometheus_config__()

            if self.area_type == 'Release':
                svc_fqdn = "eric-pm-server-external.monitoring.svc.cluster.local"
                prometheus_hostname = urlsplit(self.prometheus_monitoring_url).hostname
                logging.info(f'Prometheus Hostname: {prometheus_hostname}')

                monitoring_gateway_file = os.path.join(self.grafana_prometheus_config_files_path,
                                                       "monitoring-gateway.yaml")
                self.__update_hostname_in_rs_file__(prometheus_hostname, svc_fqdn, monitoring_gateway_file)

                monitoring_virtualservice_file = os.path.join(self.grafana_prometheus_config_files_path,
                                                              "monitoring-virtualservice.yaml")
                self.__update_hostname_in_rs_file__(prometheus_hostname, svc_fqdn, monitoring_virtualservice_file)

                monitoring_serviceentry_file = os.path.join(self.grafana_prometheus_config_files_path,
                                                            "monitoring-serviceentry.yaml")
                self.__update_hostname_in_rs_file__(prometheus_hostname, svc_fqdn, monitoring_serviceentry_file)
                prometheus_config_files = \
                    ['monitoring-gateway.yaml', 'monitoring-virtualservice.yaml', 'monitoring-serviceentry.yaml']

                self.__upload_files_from_local_to_ccd__(prometheus_config_files)

                self.__apply_monitoring_prometheus_config__()

            logging.info('Prometheus configuration executed successfully')

        except Exception:
            logging.error('Prometheus configuration failed')
            raise

    def __apply_prometheus_config__(self):
        """
        Executes commands to apply changes from prometheus-gateway and prometheus-virtualservice
        files
        """
        grafana_prometheus_config_files_directory = \
            self.__get_grafana_prometheus_config_files_directory__()

        kubectl_apply_cmd = f'/usr/local/bin/kubectl apply -f ' \
                            f'{grafana_prometheus_config_files_directory}/prometheus-gateway.yaml' \
                            f' -n {self.prometheus_namespace}'
        self.kubectl_helper.run_command(kubectl_apply_cmd)

        kubectl_apply_cmd = \
            f'/usr/local/bin/kubectl apply -f ' \
            f'{grafana_prometheus_config_files_directory}/prometheus-virtualservice.yaml ' \
            f'-n {self.prometheus_namespace}'
        self.kubectl_helper.run_command(kubectl_apply_cmd)

    def __apply_monitoring_prometheus_config__(self):
        """
        Executes commands to apply changes from prometheus-monitoring-gateway and prometheus-monitoring-virtualservice
        files
        """
        grafana_prometheus_config_files_directory = \
            self.__get_grafana_prometheus_config_files_directory__()
        kubectl_apply_cmd = \
            f'/usr/local/bin/kubectl apply -f ' \
            f'{grafana_prometheus_config_files_directory}/monitoring-gateway.yaml ' \
            f'-n {self.prometheus_namespace}'
        self.kubectl_helper.run_command(kubectl_apply_cmd)

        kubectl_apply_cmd = \
            f'/usr/local/bin/kubectl apply -f ' \
            f'{grafana_prometheus_config_files_directory}/monitoring-virtualservice.yaml ' \
            f'-n {self.prometheus_namespace}'
        self.kubectl_helper.run_command(kubectl_apply_cmd)

        kubectl_apply_cmd = \
            f'/usr/local/bin/kubectl apply -f ' \
            f'{grafana_prometheus_config_files_directory}/monitoring-serviceentry.yaml ' \
            f'-n {self.prometheus_namespace}'
        self.kubectl_helper.run_command(kubectl_apply_cmd)

    def datasource_dashboard_setup(self):
        """
        Creates Prometheus datasource, builds grafana folder.
        Updates Grafana dashboards with new folder ID
        """
        logging.debug(f"Grafana Url: {self.grafana_url}")
        logging.debug(f"Grafana User: {self.grafana_user}")
        logging.debug(f"Grafana Password: {self.grafana_password}")
        try:
            logging.info('Setting up Prometheus datasource')
            datasource_name = f'Prometheus_{self.prometheus_namespace}_{self.test_environment_name}'
            datasource_api = f'/api/datasources/name/{datasource_name}'

            if not self.__check_prometheus_datasource_exists_in_grafana__(datasource_api):
                datasource_url = self.prometheus_url
                self.__create_prometheus_datasource_in_grafana__(datasource_name, datasource_url)

            folder_name = "IDUN"
            folder_id = self.__check_if_folder_exists__(folder_name)

            if not folder_id:
                folder_id = self.__create_folder_in_grafana__(folder_name)

            logging.info(f'Grafana folder id to import dashboard is: {folder_id}')
            self.__upload_grafana_dashboards__(folder_id)

            if self.area_type == 'Release':
                logging.info('Setting up Prometheus datasource for Monitoring namespace')
                datasource_name = f'Prometheus_Monitoring_{self.test_environment_name}'
                datasource_api = f'/api/datasources/name/{datasource_name}'

                if not self.__check_prometheus_datasource_exists_in_grafana__(datasource_api):
                    datasource_url = self.prometheus_monitoring_url
                    self.__create_prometheus_datasource_in_grafana__(datasource_name, datasource_url)

                folder_name = "Monitoring"
                folder_id = self.__check_if_folder_exists__(folder_name)

                if not folder_id:
                    folder_id = self.__create_folder_in_grafana__(folder_name)

                logging.info(f'Grafana folder id to import dashboard is: {folder_id}')
                self.__upload_grafana_dashboards__(folder_id)

            elif self.area_type == 'PSO':
                logging.info('Setting up Prometheus datasource for PSO')
                datasource_name = f'Prometheus_oss-deploy_{self.test_environment_name}'
                datasource_api = f'/api/datasources/name/{datasource_name}'

                if not self.__check_prometheus_datasource_exists_in_grafana__(datasource_api):
                    datasource_url = self.prometheus__url
                    self.__create_prometheus_datasource_in_grafana__(datasource_name, datasource_url)

                folder_name = "PSO"
                folder_id = self.__check_if_folder_exists__(folder_name)

                if not folder_id:
                    folder_id = self.__create_folder_in_grafana__(folder_name)

                logging.info(f'Grafana folder id to import dashboard is: {folder_id}')
                self.__upload_grafana_dashboards__(folder_id)

        except Exception as exception:
            logging.error('Failed to setup the Grafana dashboard')
            logging.error(f'Exception: {str(exception)}')
            raise

    def __check_prometheus_datasource_exists_in_grafana__(self, prometheus_datasource_api):
        """
        Makes request to the Grafana URL to check if the prometheus datasource exists
        :param prometheus_datasource_api: grafana api url for the prometheus datasource
        :return: if the datasource exists
        :rtype: Boolean
        """
        logging.info('Checking Prometheus datasource exists in Grafana')
        response = \
            requests.get(f'{self.grafana_url}{prometheus_datasource_api}',
                         auth=(self.grafana_user,
                               self.grafana_password),
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'})
        logging.debug(f'Grafana response: {str(response.json())}')
        if response.ok:
            logging.info(f'Prometheus Datasource already exists for {self.test_environment_name}')
            return True
        return False

    def __create_prometheus_datasource_in_grafana__(self, prometheus_datasource_name, datasource_url):
        """
        Makes request to setup the Prometheus datasource in Grafana
        :param prometheus_datasource_name:
        """
        logging.info(f'Prometheus Datasource will be created for {self.test_environment_name}')

        create_req_body = self.__create_request_payload_to_create_source__(
            datasource_url,
            prometheus_datasource_name
        )

        create_datasource_response = \
            request_retry("POST", f'{self.grafana_url}/api/datasources', 5,
                          body=create_req_body,
                          auth=(self.grafana_user, self.grafana_password),
                          headers={'Accept': 'application/json', "Content-Type": "application/json"})

        logging.info(f'Prometheus Datasource created for {self.test_environment_name}')
        logging.debug(f'Create datasource response: {str(create_datasource_response.json())}')

    def __check_if_folder_exists__(self, folder_name):
        """
        Checks to see if folder exists on grafana instance
        :param folder_name: name of folder to be checked
        :return: folder_id if exists
        :rtype: str | Boolean
        """
        logging.info(f'Checking if the {folder_name} folder exists in Grafana')
        grafana_folders_response = \
            requests.get(f'{self.grafana_url}/api/folders',
                         auth=(self.grafana_user,
                               self.grafana_password),
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'})

        if grafana_folders_response.ok:
            logging.info(f'Checking if folder already exist for {self.test_environment_name}')

            for folder in grafana_folders_response.json():
                if folder['title'] == folder_name:
                    logging.info(f"Folder {folder_name} already exist for "
                                 f"{self.test_environment_name}. Returning folder ID")
                    return folder['id']
        return False

    def __create_folder_in_grafana__(self, folder_name):
        """
        Creates folder in Grafana instance
        :param folder_name: name of folder to be created
        :return: folder_id
        :rtype: str
        """
        logging.info(f'Creating folder {folder_name} in Grafana')
        response = \
            request_retry("POST", f'{self.grafana_url}/api/folders', 5,
                          body={"title": folder_name}, auth=(self.grafana_user, self.grafana_password),
                          headers={'Content-Type': 'application/json', 'Accept': 'application/json'})

        if response.ok:
            response_body = response.json()
            if 'id' in response_body:
                logging.info(f'Successfully created folder {folder_name} in Grafana')
                return response_body['id']
        raise Exception(f'Failed to create the folder {folder_name} in Grafana instance')

    def __upload_grafana_dashboards__(self, folder_id):
        """
        Uploads dashboards to Grafana instance
        :param folder_id:
        """
        logging.info('Uploading Dashboards to Grafana')
        list_of_files = utils.get_list_of_files(self.area_type)
        pattern = "*.json"
        upload_failed = False
        for file_name in list_of_files:
            if fnmatch.fnmatch(file_name, pattern):
                if self.area_type == 'Release':
                    remote_dashboard_filepath = 'grafana_prometheus_dashboards/release/' + file_name
                    DASHBOARD_FILE_PATH = CONSTANTS.get('FILE_PATHS', 'release_dashboard_runtime_file')
                elif self.area_type == 'PSO':
                    remote_dashboard_filepath = 'grafana_prometheus_dashboards/pso/' + file_name
                    DASHBOARD_FILE_PATH = CONSTANTS.get('FILE_PATHS', 'pso_dashboard_runtime_file')
                else:
                    remote_dashboard_filepath = 'grafana_prometheus_dashboards/' + file_name
                    DASHBOARD_FILE_PATH = CONSTANTS.get('FILE_PATHS', 'dashboard_runtime_file')
                utils.update_file(remote_dashboard_filepath, DASHBOARD_FILE_PATH)
                with open(DASHBOARD_FILE_PATH, 'r', encoding='utf-8') as dashboard_file:
                    dashboard_file_contents = json.load(dashboard_file)
                    try:
                        if dashboard_file_contents['dashboard']:
                            dashboard_file_contents['folderId'] = folder_id
                            dashboard_file_contents['overwrite'] = True
                            dashboard_file_contents['dashboard']['id'] = 'null'

                    except KeyError:
                        dashboard_file_contents['id'] = 'null'
                        dashboard_file_contents = {
                            "dashboard": dashboard_file_contents,
                            "folderId": folder_id,
                            "overwrite": True
                        }

                    upload_grafana_dashboard_response = \
                        request_retry("POST", f'{self.grafana_url}/api/dashboards/db', 5,
                                      body=dashboard_file_contents,
                                      auth=(self.grafana_user, self.grafana_password), ssl=True)

                    if not upload_grafana_dashboard_response.ok:
                        upload_failed = True
                        logging.error(f'Something went wrong in uploading dashboard {file_name} '
                                      f'to Grafana')
                        logging.error(f'Response details: {upload_grafana_dashboard_response.text}')
                    else:
                        logging.info(f'{file_name} dashboard uploaded successfully!')
                        logging.debug(f'Response details: {upload_grafana_dashboard_response.text}')
        if upload_failed:
            raise Exception('One or more of the dashboard uploads failed. Please check logging '
                            'above for more details.')
        logging.info('Dashboards uploaded successfully')

    def __upload_files_from_local_to_ccd__(self, config_files_to_ftp):
        """
        Method to upload config files from local environment to the director node for Red Hat Test
        Environments only
        :param: config_files_to_ftp
        """
        if self.platform_type != 'RH':
            return

        try:
            logging.debug(f"Config file location is: {self.grafana_prometheus_config_files_path}")
            logging.debug(f"Config files to FTP is: {str(config_files_to_ftp)}")

            self.__ftp_from_local_to_server__(config_files_to_ftp)

        except Exception:
            logging.error(
                "Unknown exception occurred when transfer file from local fs to director_ip:"
                f" {self.platform_operator.ccd_director_ip}")
            raise

    def __ftp_from_local_to_server__(self, config_files_to_ftp):
        """
        Copies config files from a local environment to the Jumpserver of a Red Hat environment.
        This is so that we can later copy them from the Jumpserver to the Director Node
        :param config_files_to_ftp:
        """
        test_environment_details = EnvironmentCredentialsFileParser(self.test_environment_name)

        sftp_jumpserver_connection = SFTPServerConnection(
            test_environment_details.credentials["IP"],
            test_environment_details.credentials["SSH_USER"],
            test_environment_details.credentials['SSH_PEM_FILE']
        )

        for file_name in config_files_to_ftp:
            local_file_path = f"{self.grafana_prometheus_config_files_path}/{file_name}"
            intermediate_file_path = f"/tmp/{file_name}"

            logging.debug(f"Local file path: {local_file_path}")
            logging.debug(f"Remote intermediate file path: {intermediate_file_path}")

            sftp_jumpserver_connection.copy_file_via_sftp(local_file_path, intermediate_file_path)

    @staticmethod
    def __create_request_payload_to_create_source__(datasource_url, datasource_name):
        """
        Method to create request payload
        :param datasource_url:
        :param datasource_name:
        :return: request_payload
        """
        return {
            "name": f'{datasource_name}',
            "type": "prometheus",
            "url": f'{datasource_url}',
            "access": "proxy",
            "basicAuth": False,
            "jsonData": {
                "tlsSkipVerify": True
            }
        }

    def output_useful_information(self):
        """
        Outputs useful information for the end user
        """
        logging.info('Successfully installed and configured Grafana')
        logging.info('******************')
        if self.area_type == 'Release':
            logging.info(f'Prometheus URL: {self.prometheus_monitoring_url}')
        else:
            logging.info(f'Prometheus URL: {self.prometheus_url}')
        logging.info(f'Grafana URL: {self.grafana_url}')
        logging.info(f'Grafana Password: {self.custom_grafana_password}')
        logging.info('******************')
