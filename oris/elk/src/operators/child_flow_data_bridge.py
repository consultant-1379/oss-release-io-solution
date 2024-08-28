''' importing logging, os, sys, argparse, time. module'''
import logging
import os
import sys
import argparse
from lib.elastic_lib import ElasticSearchLib
from lib.spinnaker_lib_dora import SpinnakerLib

logger = logging.getLogger(__name__)


def setLogLevel(debug):
    log = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log,
        format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")


def getArgs():
    parser = argparse.ArgumentParser(
        description="CICD Report Center data bridge script. (Requires JIRA_USERNAME, JIRA_PASSWORD)")
    parser.add_argument("-r", "--registration", dest="regId",
                        help="Register new execution with specified ID")
    parser.add_argument("-s", "--scan", dest="scan", action="store_true",
                        help="Scan ElasticSearch and JIRA and update finished or conlcuded cases")
    parser.add_argument("-m", "--minutes", dest="minutes", type=int,
                        help="Scan JIRA tickets concluded in past X minutes")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="Show DEBUG level logs")

    args = parser.parse_args()
    if (bool(args.regId) == bool(args.scan)):
        raise Exception("Please choose between registration and scan mode")
    if (bool(args.scan) and not bool(args.minutes)):
        raise Exception("Please use -m option when using scan mode")
    return args


def getCredentials():
    return os.environ['JIRA_USERNAME'], os.environ['JIRA_PASSWORD'], os.environ['JIRA_API_TOKEN']


def registerNewExecution(id, username, password):
    logger.info(f"Registering execution with ID {id}")
    logger.info("Get execution details from Spinnaker")
    spinnaker = SpinnakerLib(username, password)
    executions = spinnaker.getExecutionsById(id)
    es = ElasticSearchLib("", "", "")
    toBeRegistered = []
    for exec in executions:
        es.__init__("", "", "child-prod-report-center")
        if es.getDocumentById(exec["stage"]["id"]) is not None:
            logger.warning(
                f"Error: Stage {exec['stage']['id']} of Execution {id} is already registered!")
            continue
        # This is to frce this execution to be reprocessed during scanning
        exec["pipeline"]["finished"] = False
        toBeRegistered.append(exec)

    logger.info("Register stages in execution into ElasticSearch")
    es.updateDocuments(toBeRegistered)


def updateRegisteredExecutions(username, password):
    es = ElasticSearchLib("", "", "")
    spinnaker = SpinnakerLib(username, password)
    for i in ["child-prod-report-center"]:
        es.__init__("", "", i)
        logger.info(f"Index pattern is: {i}")
        logger.info("Finding unconcluded executions from ElasticSearch")
        toBeUpdated = es.getUnfinishedDocuments()
        logger.info(
            f"Found {len(toBeUpdated)} pending execution stages from ElasticSearch")
        pipelines = {}
        for execution in toBeUpdated:
            pipelineId = execution["pipeline"]["id"]
            if pipelineId not in pipelines:
                pipelines[pipelineId] = spinnaker.getExecutionsById(pipelineId)
            updated = next(
                x for x in pipelines[pipelineId] if x["stage"]["id"] == execution["stage"]["id"])
            execution["pipeline"] = updated["pipeline"]
            execution["stage"] = updated["stage"]
            if execution["stage"]["id"] is not None:
                if execution["stage"]["name"] == "Check is App Blocked" and execution["stage"]["status"] == "STOPPED":
                    updated["pipeline"]["status"] = "BLOCKED"
        logger.info("Execution status updated from Spinnaker")
        logger.info(
            f"Updating {len(toBeUpdated)} documents in ElasticSearch")
        es.updateDocuments(toBeUpdated)


def main() -> int:
    args = getArgs()
    setLogLevel(args.debug)
    if args.scan:
        updateRegisteredExecutions("EIAPREG100", "CztvYwveBHUp8A2UQtBxDxsB")
        return 0
    else:
        registerNewExecution(args.regId, "EIAPREG100", "CztvYwveBHUp8A2UQtBxDxsB")
        return 0
    logger.info("operations failed")


if __name__ == '__main__':
    sys.exit(main())
