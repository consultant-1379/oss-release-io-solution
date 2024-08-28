"""Importing requests, json, logging and datetime modules"""
import requests
import json
import logging
from datetime import datetime, timedelta
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.csv_lib import csvData
from elk.src.operators.lib.time_utils import TimeCalculator


class StabilityStkpiMetrics:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def getStkpiData(self):
        csvObj = csvData()
        currentTime = datetime.now()
        timeFourHoursAgo = currentTime - timedelta(hours=4)
        endTimeStamp = int(currentTime.timestamp() * 1000)
        startTimeStamp = int(timeFourHoursAgo.timestamp() * 1000)
        # get parameters from csv file
        csvParameters = csvObj.getStkpidata()
        for data in csvParameters:
            baseUlr, clusterName, namespaceName, index, metric = data["url"], data["clusterName"], data[
                "namespaceName"], data["stkpiIndex"], data["metric"]
            url = f"{baseUlr}start={startTimeStamp}&end={endTimeStamp}&cluster={clusterName}&namespace={namespaceName}"
            es = ElasticSearchLib(self.username, self.password, index)
            # get request to fetch json response of api call
            result = requests.get(url)
            if result.status_code == 200:
                data = json.loads(result.text)
                toBeUpdated = []
                for item in data:
                    record = self.extractData(item, clusterName, namespaceName, metric)
                    toBeUpdated.append(record)
                # Uploadling documents to Elasticsearch database
                logging.info(f"Updating {len(toBeUpdated)} documents to Elasticsearch")
                es.updateDocuments(toBeUpdated)
            else:
                raise Exception("Error:", result.status_code)

    def extractData(self, item, cluster, namespace, metric):
        time = TimeCalculator()
        st = {}
        # Iterate through the list of dictionaries
        st["id"] = item["execution"]
        st["average"] = item["values"]["avg"]
        st["minimum"] = item["values"]["min"]
        st["maximum"] = item["values"]["max"]
        st["median"] = item["values"]["med"]
        # Convert time value to milliseconds
        st["date"] = time.parseTimeStampToMilis(item["time"])
        st["cluster"] = cluster
        st["namespace"] = namespace
        st["metric"] = metric
        return st
