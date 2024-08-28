"""import re module."""
import re
import logging

import requests


class JenkinsLib:

    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self._auth = (username, password)

    def _getDataForJob(self, jobUrl):
        apiUrl = f"{jobUrl}/api/json"
        response = requests.get(apiUrl, auth=self._auth)
        # logging.debug(f"Response: {response.status_code} {response.text}")
        if response.ok:
            return response.json()
        return None

    def getConsoleLog(self, jobUrl):
        apiUrl = f"{jobUrl}/logText/progressiveText?start=0"
        response = requests.get(apiUrl, auth=self._auth)
        if response.ok:
            return response.text
        return None

    def getJcatLogUrl(self, jobUrl):
        data = self._getDataForJob(jobUrl)
        if data is None or "description" not in data:
            return None
        description = self._getDataForJob(jobUrl)["description"]
        if description is None:
            return None
        links = re.findall("href=[\"\'](.*?)[\"\']", description)
        for link in links:
            if "adpci.sero.wh.rnd.internal.ericsson.com/results/logs" in link:
                return link
        return None
