"""This file fetches data from jenkins"""
import requests
import json
import logging
from datetime import datetime


class JenkinsData:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server = None

    def connect_to_jenkins(self, username, password, url):
        response = requests.get(url, auth=(username, password))
        data = json.loads(response.text)
        return data

    def pipelineData(self, username, password, url, todaydate):
        data = self.connect_to_jenkins(username, password, url)
        failedJobs = [j for i in data["jobs"] if 'builds' in i for j in i['builds'] if j['result'] == "FAILURE"]
        PipelineData = {}
        count = 1
        for job in failedJobs:
            date = self.timestampToDate(job["timestamp"])
            date = str(date).split(" ")[0]
            if date == todaydate:
                jobName = str(job['url']).split("/")[-3]
                jName = jobName.lower()
                pipelineSuffixes = ["_precodereview", "_publish", "_release"]
                if any(suffix in jName for suffix in pipelineSuffixes):
                    buildNumber = job['number']
                    PipelineData[count] = [jobName, buildNumber]
                    count = count + 1
        return PipelineData

    def timestampToDate(self, timeStamp):
        timestamp_ms = timeStamp
        timestamp_s = timestamp_ms / 1000.0
        date_time = datetime.fromtimestamp(timestamp_s)
        formatted_date = date_time.strftime('%Y-%m-%d %H:%M:%S')
        return formatted_date
