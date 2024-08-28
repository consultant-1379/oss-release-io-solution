"""
This is the CLI for the OSS Release IO Solution
"""

import click
from oris.src.operators.grafana_prometheus_configuration import GrafanaPrometheusSetup
from oris.src.etc import logging_utils
from oris.src.operators.kubectl_helper import KubectlHelper


def log_verbose_option(func):
    """A decorator for the log verbose command line argument."""
    return click.option('-v', '--verbose', type=click.BOOL, is_flag=True, required=False,
                        help='Increase output verbosity')(func)


def platform_type_option(func):
    """A decorator for the platform type command line argument."""
    return click.option('-pt', '--platform_type', type=click.Choice(['KaaS', 'RH', 'AWS', 'Azure', 'CNIS', 'OCP']),
                        required=True, help='The type of platform that K8s is running on')(func)


def environment_name_option(func):
    """A decorator for the environment_name command line argument."""
    return click.option('-e', '--environment_name', type=click.STRING, required=True,
                        help='The name of the environment we are connecting to.')(func)


def area_type_option(func):
    """A decorator for the area type command line argument."""
    return click.option('-at', '--area_type', type=click.Choice(['AppStage', 'PSO', 'Release']),
                        required=False, help='The type of area that the pipeline belongs')(func)


def ccd_director_ip_option(func):
    """A decorator for the ccd director ip command line argument."""
    return click.option('-cdi', '--ccd_director_ip', type=click.STRING,
                        required=False,
                        help='The ccd director ip required for Red Hat Environments')(func)


def configfile_location_option(func):
    """A decorator for the configuration file location command line argument."""
    return click.option('-cl', '--configfile_location', type=click.STRING,
                        required=False, help='The location of the configuration file')(func)


def exec_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-et', '--exec_type', type=click.STRING, required=True,
                        help='The type of the execution (Register or Scan).')(func)


def exec_id_option(func):
    """A decorator for the spinnaker pipeline execution id command line argument."""
    return click.option('-id', '--exec_id', type=click.STRING, required=False,
                        help='The spinnaker pipeline execution id.')(func)


@click.group()
def cli_main():
    """
    The entry-point to the ORIS tool.
    Please see available options below.
    """


@cli_main.command()
@log_verbose_option
@environment_name_option
@platform_type_option
def get_namespaces(verbose, environment_name, platform_type):
    """
    Gets all namespaces on a Kubernetes environment
    :param verbose:
    :param environment_name:
    :param platform_type:
    :return:
    """
    logging_utils.initialize_logging(verbose)
    kubectl_helper = KubectlHelper(test_environment=environment_name,
                                   platform_type=platform_type)
    get_namespaces_command = '/usr/local/bin/kubectl get namespaces'
    kubectl_helper.run_command(get_namespaces_command)


@cli_main.command()
@log_verbose_option
@environment_name_option
@platform_type_option
@area_type_option
def grafana_setup(verbose, environment_name, platform_type, area_type):
    """
    Sets up a Grafana instance, Prometheus instance and Grafana Dashboards in a test environment
    :param verbose:
    :param environment_name:
    :param platform_type:
    :param area_type:
    """
    logging_utils.initialize_logging(verbose)
    grafana_prometheus_operator = GrafanaPrometheusSetup(environment_name, platform_type, area_type)
    grafana_prometheus_operator.determine_if_namespace_needs_to_be_cleared()
    grafana_prometheus_operator.install_grafana()
    grafana_prometheus_operator.configure_grafana()
    grafana_prometheus_operator.set_custom_grafana_password()
    grafana_prometheus_operator.prometheus_setup()
    grafana_prometheus_operator.datasource_dashboard_setup()
    grafana_prometheus_operator.output_useful_information()
