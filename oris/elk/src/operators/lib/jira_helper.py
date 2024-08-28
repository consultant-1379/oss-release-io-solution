'''importing requests urllib pandas module'''
import requests
import urllib
from . import record_util
import logging
from elk.src.operators.lib.time_utils import TimeCalculator


class JiraLib:

    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self._auth = (username, password)
        self._serverBaseUrl = "https://eteamproject.internal.ericsson.com"
        self._timeCal = TimeCalculator()

    def getJiraKeys(self, query):
        try:
            startAt = 0
            session = requests.Session()
            session.headers = {
                'Content-Type': 'application/json'
            }
            result = session.get(
                    f"{self._serverBaseUrl}/rest/api/2/search?jql={urllib.parse.quote(query)}"
                    f"&startAt={startAt}", auth=self._auth
                )
            keys = []
            df = result.json()["issues"]
            for i in df:
                keys.append(i["key"])
            return keys
        except ConnectionError:
            raise RuntimeError("Issuetype not available") from ConnectionError

    def getJiraType(self, key):
        try:
            session = requests.Session()
            session.headers = {
                'Content-Type': 'application/json'
            }
            result = session.get(
                    f"{self._serverBaseUrl}/rest/api/2/issue/{key}?expand=changelog",
                    auth=self._auth
                )
            if result.json().__contains__("errorMessages"):
                return None
            return result.json()["fields"]["issuetype"]["name"]
        except ConnectionError:
            raise RuntimeError("Issuetype not available") from ConnectionError

    def getJiraRecord(self, key):
        try:
            session = requests.Session()
            session.headers = {
                'Content-Type': 'application/json'
            }
            result = session.get(
                    f"{self._serverBaseUrl}/rest/api/2/issue/{key}?expand=changelog",
                    auth=self._auth
                )
            if "ESOA" in result.json()["key"]:
                return self.__esoaJiraRecords__(result.json())
            else:
                return self.__jiraRecords__(result.json())
        except ConnectionError:
            raise RuntimeError("Issuetype not available") from ConnectionError

    def __jiraRecords__(self, exec):
        jr = record_util.newEiapJiraData()
        jr["id"] = exec["key"]
        jr["url"] = f"{self._serverBaseUrl}/browse/{jr['id']}"
        jr["type"] = exec["fields"]["issuetype"]["name"]
        jr["status"] = exec["fields"]["status"]["name"]
        jr["priority"] = exec["fields"]["priority"]["name"]
        jr["resolution"] = self.__getResolutionName__(exec)
        jr["component"] = self.__getComponents__(exec)
        jr["labels"] = exec["fields"]["labels"]
        jr["assignee"] = self.__getAssignee__(exec)
        jr["reporter"] = exec["fields"]["reporter"]["displayName"]
        jr["sprint"] = self.__getSprint__(exec)
        jr["daysOpen"] = exec["fields"]["resolutiondate"]
        jr["linkedTickets"] = self.__getIssueLinks__(exec)
        jr["lastUpdated"] = self._timeCal.parseTimeStamp(exec["fields"]["updated"])
        jr["createdDate"] = self._timeCal.parseTimeStamp(exec["fields"]["created"])
        jr["issueResolvedBaseline"] = self.__getIssueResolvedBaseline__(exec)

        if "EO" in jr["id"]:
            jr["teamName"] = self.__getEoTeamName__(exec)
            jr["reporterTeamName"] = None
            jr["raTeam"] = None
        else:
            jr["teamName"] = self.__getTeamName__(exec)
            jr["reporterTeamName"] = self.__getReporterTeamName__(exec)
            if "Support" in jr["type"]:
                jr["raTeam"] = None
            else:
                jr["raTeam"] = self.__getRATeam__(exec)

        if jr["issueResolvedBaseline"] == "Yes":
            jr["closedDate"] = self.__getIssueResolvedBaselineDate__(exec)
            jr["closedDuration"] = self._timeCal.getDuration(jr['createdDate'], jr['closedDate'])
            jr["daysOpen"] = self._timeCal.getDaysOpen(jr['createdDate'], jr['closedDate'])
            if "Closed" in jr["status"] or "Done" in jr["status"]:
                jr["concluded"] = True
            else:
                jr["concluded"] = False
        else:
            jr["closedDate"] = self._timeCal.parseTimeStamp(exec["fields"]["resolutiondate"])
            jr["closedDuration"] = self._timeCal.getDuration(jr['createdDate'], jr['closedDate'])
            if jr["closedDuration"]:
                if jr["closedDuration"] < 24 * 3600 * 1000:
                    jr["daysOpen"] = self._timeCal.getHoursOpen(jr['createdDate'], jr['closedDate'])
                    jr["concluded"] = True
                else:
                    jr["daysOpen"] = self._timeCal.getDaysOpen(jr['createdDate'], jr['closedDate'])
                    jr["concluded"] = True
        return jr

    def __esoaJiraRecords__(self, exec):
        jr = record_util.newEsoaJiraData()
        jr["id"] = exec["key"]
        jr["url"] = f"{self._serverBaseUrl}/browse/{jr['id']}"
        jr["type"] = exec["fields"]["issuetype"]["name"]
        jr["status"] = exec["fields"]["status"]["name"]
        jr["priority"] = exec["fields"]["priority"]["name"]
        jr["resolution"] = self.__getResolutionName__(exec)
        jr["component"] = self.__getComponents__(exec)
        jr["labels"] = exec["fields"]["labels"]
        jr["assignee"] = self.__getAssignee__(exec)
        jr["reporter"] = exec["fields"]["reporter"]["displayName"]
        jr["linkedTickets"] = self.__getIssueLinks__(exec)
        jr["sprint"] = self.__getSprint__(exec)
        jr["teamName"] = self.__getTeamName__(exec)
        jr["lastUpdated"] = self._timeCal.parseTimeStamp(exec["fields"]["updated"])
        jr["createdDate"] = self._timeCal.parseTimeStamp(exec["fields"]["created"])
        jr["daysOpen"] = exec["fields"]["resolutiondate"]
        jr["closedDate"] = self._timeCal.parseTimeStamp(exec["fields"]["resolutiondate"])
        jr["closedDuration"] = self._timeCal.getDuration(jr['createdDate'], jr['closedDate'])
        if jr["closedDuration"]:
            if jr["closedDuration"] < 24 * 3600 * 1000:
                jr["daysOpen"] = self._timeCal.getHoursOpen(jr['createdDate'], jr['closedDate'])
                jr["concluded"] = True
            else:
                jr["daysOpen"] = self._timeCal.getDaysOpen(jr['createdDate'], jr['closedDate'])
                jr["concluded"] = True
        return jr

    def __getResolutionName__(self, record):
        if record["fields"]["resolution"] is not None:
            return record["fields"]["resolution"]["name"]
        else:
            return None

    def __getComponents__(self, issue):
        components = []
        componentsList = issue["fields"]["components"]
        for i in componentsList:
            if "name" in i:
                componentName = i["name"]
                components.append(componentName)
        return components

    def __getAssignee__(self, record):
        if record["fields"]["assignee"] is not None:
            return record["fields"]["assignee"]["displayName"]
        else:
            return None

    def __getSprint__(self, issue):
        sprint = []
        sprintList = issue["fields"]["customfield_11910"]
        if sprintList is not None:
            for i in sprintList:
                sprintName = i.split(",")[3].split("=")[1]
                sprint.append(sprintName)
        return sprint

    def __getTeamName__(self, record):
        if record["fields"]["customfield_18213"] is not None:
            return record["fields"]["customfield_18213"]["value"]
        else:
            return None

    def __getRATeam__(self, record):
        if record["fields"]["customfield_18644"] is not None:
            return record["fields"]["customfield_18644"]["value"]
        else:
            return None

    def __getEoTeamName__(self, record):
        if record["fields"]["customfield_15527"] is not None:
            return record["fields"]["customfield_15527"]["value"]
        else:
            return None

    def __getReporterTeamName__(self, record):
        if record["fields"]["customfield_38999"] is not None:
            return record["fields"]["customfield_38999"]["value"]
        else:
            return None

    def __getIssueLinks__(self, issue):
        issueLinks = []
        linkedJiras = issue["fields"]["issuelinks"]
        for i in linkedJiras:
            if "outwardIssue" in i:
                issueKey = i["outwardIssue"]["key"]
                issueLinks.append(
                    {"key": issueKey, "url": f"{self._serverBaseUrl}/browse/{issueKey}"})
        remoteLinks = self.__getIssueRemoteLinks__(issue["key"])
        for r in remoteLinks:
            issueLinks.append(
                {"key": r["object"]["title"], "url": r["object"]["url"]})
        return issueLinks

    def __getIssueRemoteLinks__(self, issueId):
        try:
            session = requests.Session()
            session.headers = {
                'Content-Type': 'application/json'
            }
            response = session.get(
                    f"{self._serverBaseUrl}/rest/api/2/issue/{issueId}/remotelink",
                    auth=self._auth
                )
            self._logger.debug(response)
            return response.json()
        except ConnectionError:
            raise RuntimeError("Issuetype not available") from ConnectionError

    def __getIssueResolvedBaseline__(self, record):
        changes = record["changelog"]["histories"]
        baseline = []
        for i in changes:
            items = i["items"]
            for item in items:
                if "Issue Resolved in Baseline" in str(item):
                    baseline.append(item["toString"])
        if len(baseline) != 0:
            return baseline[-1]
        return None

    def __getIssueResolvedBaselineDate__(self, record):
        changes = record["changelog"]["histories"]
        createdTime = []
        for i in changes:
            items = i["items"]
            for item in items:
                if "Issue Resolved in Baseline" in str(item):
                    createdTime.append(i["created"])
        if len(createdTime) != 0:
            timeStamp = self._timeCal.parseTimeStamp(createdTime[-1])
            return timeStamp
        return None
