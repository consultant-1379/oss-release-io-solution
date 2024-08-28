"""import requests module"""
import logging
import requests
from . import record_util


class TeamLib:

    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self._auth = (username, password)
        self._serverBaseUrl = "https://pdu-oss-tools1.seli.wh.rnd.internal.ericsson.com/"
        self._queryUrl = self._serverBaseUrl + "team-inventory/api/teams"

    def fetchTeam(self):
        response = requests.get(self._queryUrl, auth=self._auth)
        self._logger.debug(response, response.text)
        teams = []
        for team in response.json():
            if team["program"] is not None and "Aeonic" in team["program"]:
                teams.append(self._toTeamRecord(team))
        return teams

    def _toTeamRecord(self, team, app, ms):
        tr = record_util.newTeamData()
        tr["teamName"] = team["name"]
        tr["app"] = app
        tr["program"] = team["program"]
        tr["microservice"] = ms
        return tr

    def getTeamRecord(self, ms, app):
        response = requests.get(self._queryUrl, auth=self._auth)
        if response.status_code == 200:
            self._logger.debug(response, response.text)
            if "eric-oss" in app:
                app = app.split("eric-oss-")[1]
            if "_Platform_Staging" in app:
                app = app.split("_Platform_Staging")[0]
            if "_Baseline_Staging" in app:
                app = app.split("_Baseline_Staging")[0]
            if "-E2E-Flow" in ms:
                ms = ms.split("-E2E-Flow")[0]
            for item in response.json():
                if item["microservice"] is not None:
                    if item["microservice"] or item["microservice"] not in ["NA", "N/A"]:
                        if ms and ms.capitalize() in item["microservice"] or app in item["microservice"]:
                            return self._toTeamRecord(item, app, ms)
            tr = record_util.newTeamData()
            tr["app"] = app
            tr["microservice"] = f"{ms} Not Defined"
        else:
            tr = record_util.newTeamData()
            tr["app"] = ""
            tr["microservice"] = ""
        return tr
