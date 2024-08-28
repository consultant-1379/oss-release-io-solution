""" import logging module"""
import logging
from elk.src.operators.lib.jira_helper import JiraLib
from elk.src.operators.lib.elastic_lib import ElasticSearchLib


class JiraDataBridge:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.jira = JiraLib(username, password)
        self.eicQuery = "project in (IDUN) AND (issuetype = TR) AND status not in (closed, done)"
        self.eicReleaseQuery = "project in (IDUN, EO) AND type in (support, bug, tr) AND labels = EIAP_TopBlocker \
            AND status not in (closed, done)"
        self.eoQuery = "project = EO AND issuetype in (Bug, Support) AND priority in (Critical, Blocker) \
            AND labels = EO_AppStaging_Support AND status != Closed"
        self.autoappsQuery = "project = IDUN AND issuetype in (Bug, Support) AND status in (Closed, Done) \
            AND cf[18213] = Sirius"
        self.esoaQuery = "project = ESOA AND issuetype in (TR, Bug, Support) AND status not in (Resolved, Done) \
                    AND priority in (A, B, C)"

    def executorJira(self):
        reOpenedEIC = "project in (IDUN) AND issuetype in (TR) AND priority in (Blocker) AND status \
            CHANGED FROM (Closed, Done) AND status CHANGED AFTER startOfDay(-30d)"
        reOpecnedEO = "project = EO AND issuetype in (Bug, Support) AND priority in (Critical, Blocker) \
            AND labels = EO_AppStaging_Support AND status CHANGED FROM (Closed, Done) AND status \
                  CHANGED AFTER startOfDay(-30d)"
        eicList, eicRelaseList, eoList, autoappsList, esoaList = self.getJiraKeys()
        reOpenedEICList, reOpenedEOList = self.jira.getJiraKeys(reOpenedEIC), self.jira.getJiraKeys(reOpecnedEO)
        eicJiraKeys = (list(set(eicList)) + list(set(reOpenedEICList))) + list(set(eicRelaseList) - set(eicList))
        eoJirakeys = (list(set(eoList+reOpenedEOList)))
        autoappsJiraKeys = (list(set(autoappsList)))
        esoaJiraKeys = (list(set(esoaList)))
        tickets = [eicJiraKeys, eoJirakeys, autoappsJiraKeys, esoaJiraKeys]
        for product in tickets:
            if eicJiraKeys == product:
                self.registerJiraRecords(eicJiraKeys, "eiap-jira-center")
            elif eoJirakeys == product:
                self.registerJiraRecords(eoJirakeys, "eo-jira-center")
            elif autoappsJiraKeys == product:
                self.registerJiraRecords(autoappsJiraKeys, "autoapps-jira-center")
            elif esoaJiraKeys == product:
                self.registerJiraRecords(esoaJiraKeys, "esoa-jira-center")
            else:
                pass

    def getJiraKeys(self):
        eicList = self.jira.getJiraKeys(self.eicQuery)
        eicReleaseList = self.jira.getJiraKeys(self.eicReleaseQuery)
        eoList = self.jira.getJiraKeys(self.eoQuery)
        autoappsList = self.jira.getJiraKeys(self.autoappsQuery)
        esoaList = self.jira.getJiraKeys(self.esoaQuery)
        return eicList, eicReleaseList, eoList, autoappsList, esoaList

    def getArea(self, jiraID):
        eicList, eicReleaseList, eoList, autoappsList, esoaList = self.getJiraKeys()
        if jiraID in eicList and eicReleaseList:
            return ["Overall", "Release"]
        elif jiraID in eicReleaseList:
            return ["Release"]
        elif jiraID in eicList:
            return ["Overall"]
        elif jiraID in eoList:
            return ["EO"]
        elif jiraID in autoappsList:
            return ["autoapps"]
        elif jiraID in esoaList:
            return ["ESOA"]
        else:
            return None

    def registerJiraRecords(self, tickets, index):
        documents = []
        es = ElasticSearchLib(self.username, self.password, index)
        logging.info(f"Tickets found: {tickets}")
        logging.info(f"Total number of tickets found open in {index}: {len(tickets)}")
        for i in tickets:
            if es.getDocumentById(i) is None:
                logging.info(f"{i} not found in elasticsearch index")
                record = self.jira.getJiraRecord(i)
                documents.append(record)
                if record is not None:
                    record['area'] = self.getArea(i)
                    documents.append(record)
            else:
                logging.info(f"{i} found in elasticsearch index")
                esRecord = es.getDocumentById(i)
                jiraRecord = self.jira.getJiraRecord(i)
                if esRecord["status"] == "Done" and jiraRecord["status"] == "Closed":
                    esRecord["status"] = jiraRecord["status"]
                    documents.append(esRecord)
                elif esRecord["status"] == "Closed" or esRecord["status"] == "Done":
                    if jiraRecord["status"] != esRecord["status"]:
                        esRecord["concluded"] = "false"
                        esRecord["status"] = jiraRecord["status"]
                        esRecord["daysOpen"] = None
                        esRecord["closedDate"] = None
                        esRecord["closedDuration"] = None
                        esRecord['area'] = self.getArea(i)
                        documents.append(esRecord)
        logging.info(f"Fetched {len(documents)} new Jira records of open tickets")
        if len(documents) > 0:
            logging.info(f"Document list to be updated to ES {index}: {documents}")
            es.updateDocuments(documents)
            logging.info(f"Successfully updated {len(documents)} documents in {index}")
        else:
            logging.info("Found no new Jira records to register")
        self.updateJiraRecords(index)

    def updateJiraRecords(self, index):
        es = ElasticSearchLib(self.username, self.password, index)
        tickets = es.getUnfinishedDocuments()
        logging.info(f"Number of Unconcluded Jira found in {index}: {len(tickets)}")
        documents = []
        jiraType = ['TR', 'Support', 'Bug']
        if tickets is not None:
            for ticket in tickets:
                logging.info(f"Executing for {ticket['id']}")
                if self.jira.getJiraType(ticket['id']) in jiraType:
                    logging.info(f"Getting {ticket['id']} record")
                    record = self.jira.getJiraRecord(ticket['id'])
                    if record is not None:
                        record['area'] = ticket['area']
                        documents.append(record)
                else:
                    if self.jira.getJiraType(ticket['id']) is None:
                        es.deleteDocument(ticket['id'])
                        logging.info(f"{ticket['id']} has been deleted")
                    else:
                        logging.info(f"{ticket['id']} is no more of type {ticket['type']}")
                        es.updateDocumentConclusion(ticket['id'], self.jira.getJiraType(ticket['id']))
                        logging.info(f"{ticket['id']} has been updated in {index}")
        logging.info(f"Fetched {len(documents)} latest Jira updates")
        if len(documents) > 0:
            es.updateDocuments(documents)
            logging.info(f"Successfully updated documents in {index}")
        else:
            logging.info("Found no new Jira records to update")
