"""
This is the CLI for the OSS Release IO Solution
"""

import click
from elk.src.operators.data_bridge_image import DoraMetricsSetup
from elk.src.operators.child_data_bridge_image import ChildDoraMetricsSetup
from elk.src.operators.e2e_dora_image import E2EDoraSetupMetrics
from elk.src.operators.jira_data_bridge_image import JiraDataBridge
from elk.src.operators.elasticsearch_backup_data_bridge import BackupSetup
from elk.src.operators.rpt_data_bridge_image import rptDataBridge
from elk.src.operators.bfa_microservices_image import bfaDataBridge
from elk.src.operators.bfa_app_prod_image import bfaAppProdMetricsSetup
from elk.src.operators.validate_mongoData_image import mongoDataValidation
from elk.src.operators.index_mapping import IndexMapping
from elk.src.operators.parameterized_data_bridge_image import ParameterizedDoraSetup
from elk.src.operators.mttr_app_image import AppMTTRBridge
from elk.src.operators.team_data_bridge_image import TeamsDataSetup
from elk.src.operators.db_as_code_image import DbAsCode
from elk.src.operators.upgrade_install_image import UpgradeInstallMetrics
from elk.src.operators.stability_stkpi_image import StabilityStkpiMetrics
from elk.src.operators.update_pso_failure_image import ElasticQueryExecutor
from elk.src.operators.mttr_prod_image import ProdMTTRBridge
from elk.src.etc import logging_utils


def log_verbose_option(func):
    """A decorator for the log verbose command line argument."""
    return click.option('-v', '--verbose', type=click.BOOL, is_flag=True, required=False,
                        help='Increase output verbosity')(func)


def exec_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-et', '--exec_type', type=click.STRING, required=True,
                        help='The type of the execution (Register or Scan).')(func)


def exec_id_option(func):
    """A decorator for the spinnaker pipeline execution id command line argument."""
    return click.option('-id', '--exec_id', type=click.STRING, required=False,
                        help='The spinnaker pipeline execution id.')(func)


def username_option(func):
    """A decorator for the username command line argument."""
    return click.option('-user', '--username', type=click.STRING, required=True,
                        help='Provide username to login into spinnaker.')(func)


def password_option(func):
    """A decorator for the password command line argument."""
    return click.option('-pass', '--password', type=click.STRING, required=True,
                        help='Provide password to login into spinnaker).')(func)


def seli_username_option(func):
    """A decorator for the username command line argument."""
    return click.option('-seli_user', '--seli_username', type=click.STRING, required=True,
                        help='Provide username to login into spinnaker.')(func)


def seli_password_option(func):
    """A decorator for the password command line argument."""
    return click.option('-seli_pass', '--seli_password', type=click.STRING, required=True,
                        help='Provide password to login into spinnaker).')(func)


def timestamp_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-ts', '--time_stamp', type=click.STRING, required=True,
                        help='data view timestamp field')(func)


def index_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-index', '--index_name', type=click.STRING, required=True,
                        help='Index name for mapping')(func)


def custom_id_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-custid', '--custom_id', type=click.STRING, required=True,
                        help='Custom ID of the Dashbboard')(func)


def kibana_space_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-kib_space', '--kibana_space', type=click.STRING, required=True,
                        help='Kibana Space value')(func)


def dashboard_type_option(func):
    """A decorator for the execution type command line argument."""
    return click.option('-db_type', '--dashboard_type', type=click.STRING, required=True,
                        help='Kibana dashboard type')(func)


@click.group()
def cli_main():
    """
    The entry-point to the ORIS tool.
    Please see available options below.
    """


@cli_main.command()
@log_verbose_option
@username_option
@password_option
@exec_option
@exec_id_option
def dora_setup(verbose, username, password, exec_type, exec_id):
    """
    Registers or scans DORA metrics from spinnaker
    :param verbose:
    :param username:
    :param password:
    :param exec_type:
    :param exec_id:
    """
    logging_utils.initialize_logging(verbose)
    dora_metrics_operator = DoraMetricsSetup(username, password, exec_type, exec_id)
    dora_metrics_operator.executor()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
@exec_option
@exec_id_option
def parameter_setup(verbose, username, password, exec_type, exec_id):
    """
    Registers or scans DORA metrics from spinnaker
    :param verbose:
    :param username:
    :param password:
    :param exec_type:
    :param exec_id:
    """
    logging_utils.initialize_logging(verbose)
    dora_metrics_operator = ParameterizedDoraSetup(username, password, exec_type, exec_id)
    dora_metrics_operator.executor()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
@exec_option
@exec_id_option
def child_dora_setup(verbose, username, password, exec_type, exec_id):
    """
    Registers or scans DORA metrics from spinnaker for child pipelines
    :param verbose:
    :param username:
    :param password:
    :param exec_type:
    :param exec_id:
    """
    logging_utils.initialize_logging(verbose)
    dora_metrics_operator = ChildDoraMetricsSetup(username, password, exec_type, exec_id)
    dora_metrics_operator.executor()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def e2e_dora_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    e2e = E2EDoraSetupMetrics(username, password)
    e2e.leadTimeCal()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def jira_setup(verbose, username, password):
    """
    Registers or Update the EIC and EO Jira Tickets from Jira Board
    :param verbose:
    :param username:
    :param password:
    :param instance:
    """
    logging_utils.initialize_logging(verbose)
    Jira_board_Operator = JiraDataBridge(username, password)
    Jira_board_Operator.executorJira()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
@seli_username_option
@seli_password_option
def elk_backup_setup(verbose, username, password, seli_username, seli_password):
    """
    Registers or Update the ESOA Jira Tickets from Jira Board
    :param verbose:
    :param username:
    :param password:
    :param instance:
    """
    logging_utils.initialize_logging(verbose)
    elk_backup_operator = BackupSetup(username, password, seli_username, seli_password)
    elk_backup_operator.elasticServiceStatus()
    elk_backup_operator.filterLiveIndices()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def rpt_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    rpt = rptDataBridge(username, password)
    rpt.rptFunctions()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def bfa_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    bfa = bfaDataBridge(username, password)
    bfa.getMongoData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def bfa_app_prod_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    bfaAppProd = bfaAppProdMetricsSetup(username, password)
    bfaAppProd.getMongoData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def mongo_data_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    validate = mongoDataValidation(username, password)
    validate.getJenkinsData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
@index_option
@timestamp_option
def index_setup(verbose, username, password, index_name, time_stamp):
    logging_utils.initialize_logging(verbose)
    index_mapping = IndexMapping(username, password)
    index_mapping.mapIndex(index_name, time_stamp)


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def app_mttr_data_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    mttrCalculation = AppMTTRBridge(username, password)
    mttrCalculation.getMttrDocData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def teams_data_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    teamsData = TeamsDataSetup(username, password)
    teamsData.getTeamsData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
@seli_username_option
@seli_password_option
@custom_id_option
@kibana_space_option
@dashboard_type_option
def db_as_code_setup(verbose, username, password, seli_username, seli_password, custom_id, kibana_space,
                     dashboard_type):
    """
    Update the ndjson files
    :param verbose:
    :param username:
    :param password:
    :param seli_username:
    :param seli_password:
    :param custom_id:
    """
    logging_utils.initialize_logging(verbose)
    db_as_code_operator = DbAsCode(username, password, seli_username, seli_password, kibana_space, dashboard_type)
    db_as_code_operator.checkCustomIdStatus(custom_id)


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def upgrade_install_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    upgradeOperator = UpgradeInstallMetrics(username, password)
    upgradeOperator.getUpgradeApplicationsData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def stability_stkpi_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    st = StabilityStkpiMetrics(username, password)
    st.getStkpiData()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def update_pso_failure_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    ps = ElasticQueryExecutor(username, password)
    ps.executeElasticQuery()


@cli_main.command()
@log_verbose_option
@username_option
@password_option
def prod_mttr_data_setup(verbose, username, password):
    logging_utils.initialize_logging(verbose)
    mttrCalculation = ProdMTTRBridge(username, password)
    mttrCalculation.getMttrDocData()
