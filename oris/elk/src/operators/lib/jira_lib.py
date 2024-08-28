""""
from urllib.parse import urljoin
from . import record_util
import logging
import urllib
import requests


class JiraLib():

    def __init__(self, username, password, jenkins):
        self._logger = logging.getLogger(__name__)
        self._serverBaseUrl = "https://jira-oss.seli.wh.rnd.internal.ericsson.com"
        self._jenkins = jenkins
        self._auth = (username, password)

    def search(self, jql, fields=""):

        Run jira query
        :param jql: query string (unquoted)
        :param fields: fields to be included in query result
        :return: query result in json

        self._logger.debug(
            f"Going to run JIRA query {jql} and requesting fields {fields}")
        if fields != "":
            fields = "&fields=" + fields
        startAt = 0
        result = []
        while True:
            self._logger.debug("Query from index " + str(startAt))
            response = requests.get(f"{self._serverBaseUrl}/rest/api/2/search?jql={urllib.parse.quote(jql)}"
                                    f"&startAt={startAt}{fields}", auth=self._auth)
            self._logger.debug(response)
            total = response.json()["total"]
            maxResults = response.json()["maxResults"]
            result.extend(response.json()["issues"])
            if total > (maxResults + startAt):
                startAt = startAt + maxResults
            else:
                break

        return result

    def getLatestConcludedIssues(self, sinceMinutes):
        query = f"project = IDUN and cf[32858] = Regulus and resolution != Unresolved and updated >= -{sinceMinutes}m"
        result = self.search(query)
        return result

    def _formatId(self, execId, stageId):
        return execId + "," + stageId

    def _getIssuesById(self, execId, stageId):
        query = f"project = IDUN and cf[14210] ~ '{self._formatId(execId, stageId)}'"
        result = self.search(query)
        return result

    def _getIssueRemoteLinks(self, issueId):
        response = requests.get(
            f"{self._serverBaseUrl}/rest/api/2/issue/{issueId}/remotelink", auth=self._auth)
        self._logger.debug(response)
        return response.json()

    def _uploadStringAsAttachment(self, issueId, filename, string):
        files = {'file': (filename, string)}
        response = requests.post(
            f"{self._serverBaseUrl}/rest/api/2/issue/{issueId}/attachments", auth=self._auth, files=files)
        self._logger.debug(response)

    def _buildDescription(self, pipeline, stage, jcatLogUrl):
        if pipeline['buildNumber'] != -1:
            description = f"Trigger: *{pipeline['service']} #{pipeline['buildNumber']}*\r\n\r\n"
        else:
            description = f"Trigger: *{pipeline['service']}*\r\n\r\n"
        if pipeline['chartName'] != "":
            description += f"Helm chart: *{pipeline['chartName']}, {pipeline['chartVersion']}*\r\n\r\n"

        description += f"Failing pipeline: *{pipeline['name']}*, Stage: *{stage['name']}*\r\n\r\n"

        if stage["status"]:
            description += f"Stage execution status: *{stage['status']}*\r\n\r\n"
        description += f"Link to Spinnaker execution: [{pipeline['id']}|{pipeline['url']}]\r\n\r\n"
        if stage["jobUrl"]:
            description += f"Link to Jenkins job: [{stage['jobFullDisplayName']}|{stage['jobUrl']}]\r\n\r\n"
        if jcatLogUrl:
            description += f"Link to JCAT log: [JCAT Log|{jcatLogUrl}]\r\n\r\n"
        return description

    def createNewTicket(self, record):
        stage = record["stage"]
        pipeline = record["pipeline"]

        existingTickets = self._getIssuesById(pipeline['id'], stage["id"])
        if len(existingTickets) != 0:
            self._addJiraData(record, existingTickets[0])
            return

        if pipeline["chartName"] != "":
            summary = "{} :: {} @ {} :: {}".format(
                pipeline["chartName"], pipeline["chartVersion"], pipeline["name"], stage["name"])
        else:
            summary = "{} @ {} :: {}".format(
                self._toDateString(pipeline["startTime"], formatStr="%Y-%m-%d %H:%M"), pipeline["name"], stage["name"])

        jcatLogUrl = self._jenkins.getJcatLogUrl(
            stage['jobUrl']) if stage["jobUrl"] and stage["type"] == "jenkins" else None

        description = self._buildDescription(pipeline, stage, jcatLogUrl)
        priority = "Blocker" if stage["status"] == "FAILED_CONTINUE" else "Minor"
        fields = {
            "project": {"key": "IDUN"},
            "issuetype": {"name": "Support"},
            "priority": {"name": priority},
            "summary": summary,
            "customfield_14210": self._formatId(pipeline["id"], stage["id"]),
            "description": description
        }
        response = requests.post(self._serverBaseUrl + "/rest/api/2/issue",
                                 auth=self._auth, json={"fields": fields})
        response.raise_for_status()
        self._addJiraData(record, response.json())
        self._logger.info(f"New ticket created for execution {pipeline['id']}, stage {stage['name']}.")
        self._logger.info(f"JIRA ticket key {record['jira']['key']}")

        if stage["jobUrl"] and stage["type"] == "jenkins" and not jcatLogUrl:
            self._uploadStringAsAttachment(
                record['jira']['key'], "jenkins_console_log.txt", self._jenkins.getConsoleLog(stage["jobUrl"]))

    def _addJiraData(self, record, jiraTicket):
        record["jira"] = record_util.newJiraData()
        record["jira"]["key"] = jiraTicket["key"]
        record["jira"]["url"] = f"{self._serverBaseUrl}/browse/{record['jira']['key']}"

    def _toDateString(self, dateObject, formatStr="%Y-%m-%dT%H:%M:%S.000%z"):
        return dateObject.astimezone().strftime(formatStr)



    def loadConclusion(self, record, issue):
        stage = record["stage"]
        jira = record["jira"]
        if stage["id"] == stageId:
            jira["manuallyConcludedCause"] = [self._getIssueRootCause(issue)]
            jira["linkedTickets"] = self._getIssueLinks(issue)
            jira["manualConclusion"] = True
        else:
            self._logger.error(
                f"JIRA ID {stageId} does not match stage ID {stage['id']}")

    def getIssueId(self, issue):
        separateIdString = issue["fields"]["customfield_14210"].split(",")
        self._logger.info(separatedIdString)
        return {"exec": separateIdString[0], "stage": separateIdString[0]}



    def _getIssueRootCause(self, issue):
        conclusion = issue["fields"]["status"]["name"]
        prefix = "Closed: "
        if conclusion.startswith(prefix):
            conclusion = conclusion[len(prefix):]
        return conclusion

    def _getIssueLinks(self, issue):
        issueLinks = []
        linkedJiras = issue["fields"]["issuelinks"]
        for i in linkedJiras:
            if "inwardIssue" in i:
                issueKey = i["inwardIssue"]["key"]
                baseUrl = urljoin(i["inwardIssue"]["self"], "/")
                issueLinks.append(
                    {"key": issueKey, "url": f"{baseUrl}browse/{issueKey}"})

        remoteLinks = self._getIssueRemoteLinks(issue["key"])
        for r in remoteLinks:
            issueLinks.append(
                {"key": r["object"]["title"], "url": r["object"]["url"]})
        return issueLinks

"""
