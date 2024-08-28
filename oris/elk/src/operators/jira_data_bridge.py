''' importing logging, os, sys, argparse, module'''
import argparse
import logging
from lib.jira_helper import JiraLib
from lib.elastic_lib import ElasticSearchLib
import sys
import os

username = "EIAPREG100"
password = "CztvYwveBHUp8A2UQtBxDxsB"

jira = JiraLib(username, password)
jiraIndex = "eiap-jira-center"
es = ElasticSearchLib("", "", jiraIndex)
logger = logging.getLogger(__name__)
eicQuery = "project in (IDUN) AND (issuetype = TR) AND status not in (closed, done)"
eicReleaseQuery = "project in (IDUN, SM, CIS) AND type in (support, bug, tr) AND labels = EIAP_TopBlocker " \
                   "AND status not in (closed, done)"
eoQuery = "project = SM AND issuetype in (Bug, Support) AND priority in (Critical, Blocker) \
    AND labels = EO_AppStaging_Support AND status != Closed"


def setLogLevel(debug):
    log = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log,
        format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")


def getArgs():
    parser = argparse.ArgumentParser(
        description="EIAP JIRA Report Center data bridge script. (Requires JIRA_USERNAME, JIRA_PASSWORD)")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="Show DEBUG level logs")
    args = parser.parse_args()
    return args


def getCredentials():
    return os.environ['JIRA_USERNAME'], os.environ['JIRA_PASSWORD'], os.environ['JIRA_API_TOKEN']


def getJiraKeys():
    eicList = jira.getJiraKeys(eicQuery)
    eicReleaseList = jira.getJiraKeys(eicReleaseQuery)
    eoList = jira.getJiraKeys(eoQuery)
    return eicList, eicReleaseList, eoList


def getArea(jiraID):
    eicList, eicReleaseList, eoList = getJiraKeys()
    if jiraID in eicList and eicReleaseList:
        return ["Overall", "Release"]
    elif jiraID in eicReleaseList:
        return ["Release"]
    elif jiraID in eicList:
        return ["Overall"]
    elif jiraID in eoList:
        return ["EO"]
    else:
        return None


def registerJiraRecords():
    documents = []
    eicList, eicRelaseList, eoList = getJiraKeys()
    jiraKeys = (list(set(eicList)) + list(set(eoList))) + list(set(eicRelaseList) - set(eicList))
    logger.info(f"Tickets found : {jiraKeys}")
    logger.info(f"Total number of tickets found open {len(jiraKeys)}")
    for i in jiraKeys:
        if es.getDocumentById(i) is None:
            logger.info(f"{i} not found in elasticsearch index")
            record = jira.getJiraRecord(i)
            documents.append(record)
            if record is not None:
                record['area'] = getArea(i)
                documents.append(record)
        else:
            logger.info(f"{i} found in elasticsearch index")
            esStatus = es.getDocumentById(i)["status"]
            jiraStatus = jira.getJiraRecord(i)["status"]
            if esStatus != jiraStatus:
                record = jira.getJiraRecord(i)
                record['area'] = getArea(i)
                documents.append(record)

    logger.info(f"Fetched {len(documents)} new Jira records of open tickets")
    if len(documents) > 0:
        logger.debug(f"Document list to be updated to ES: {documents}")
        es.updateDocuments(documents)
        logger.info(f"Successfully updated {len(documents)} documents")
    else:
        logger.info("Found no new Jira records to register")


def updateJiraRecords():
    tickets = es.getUnfinishedDocuments()
    logger.info(f"Number of Unconcluded Jira found: {len(tickets)}")
    documents = []
    jiraType = ['TR', 'Support', 'Bug']
    if tickets is not None:
        for ticket in tickets:
            logger.info(f"Executing for {ticket['id']}")
            if jira.getJiraType(ticket['id']) in jiraType:
                logger.info(f"Getting {ticket['id']} record")
                record = jira.getJiraRecord(ticket['id'])
                if record is not None:
                    record['area'] = ticket['area']
                    documents.append(record)
            else:
                if jira.getJiraType(ticket['id']) is None:
                    es.deleteDocument(ticket['id'])
                    logger.info(f"{ticket['id']} has been deleted")
                else:
                    logger.info(f"{ticket['id']} is no more of type {ticket['type']}")
                    es.updateDocumentConclusion(ticket['id'], jira.getJiraType(ticket['id']))
                    logger.info(f"{ticket['id']} has been updated in {jiraIndex}")
    logger.info(f"Fetched {len(documents)} latest Jira updates")
    if len(documents) > 0:
        es.updateDocuments(documents)
        logger.info("Successfully updated documents")
    else:
        logger.info("Found no new Jira records to update")


def main() -> int:
    args = getArgs()
    setLogLevel(args.debug)
    registerJiraRecords()
    updateJiraRecords()


if __name__ == '__main__':
    sys.exit(main())
