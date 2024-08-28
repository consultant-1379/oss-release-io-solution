import logging
import requests
import json
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.spinnaker_lib import SpinnakerLib


class UpgradeInstallMetrics:
    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self.username = username
        self.password = password
        self.auth = (username, password)
        self.serverBaseUrl = "https://elastic.hahn130.rnd.gic.ericsson.se/"

    def getUpgradePipelinesData(self):
        relChildFlowUrl = (f"{self.serverBaseUrl}child-release-staging-data/_search?q=(pipeline.status:SUCCEEDED%20"
                           f"OR%20TERMINAL)AND%20pipeline.endTime:[now-6h%20TO%20now]&size=10000")
        prodUrl = (f"{self.serverBaseUrl}product-staging-data/_search?q=pipeline.name:product-staging%20AND%20"
                   f"(pipeline.status:TERMINAL%20OR%20pipeline.status:SUCCEEDED)%20AND%20pipeline.endTime:"
                   f"[now-6h%20TO%20now]&size=10000")
        stabilityUrl = (f"{self.serverBaseUrl}pe-stability-staging-data/_search?q="
                        "(pipeline.status:SUCCEEDED%20OR%20TERMINAL)AND%20pipeline.endTime:[now-6h%20TO%20now]&"
                        "size=10000")
        releaseParentFlowlUrl = (f"{self.serverBaseUrl}release-staging-data/_search?q=(pipeline.status:SUCCEEDED%20OR"
                                 f"%20pipeline.status:TERMINAL)%20AND%20(pipeline.name:Scheduled_eic-baseline-II%20AND%"
                                 f"20pipeline.name:eic-release-install-flow)"
                                 f"%20AND%20pipeline.endTime:[now-6h%20TO%20now]&size=10000")
        appUrl = (f"{self.serverBaseUrl}child-app-staging-data/_search?q=pipeline.name:Deployment_verification%20AND%20"
                  "(pipeline.status:SUCCEEDED%20OR%20TERMINAL)AND%20pipeline.endTime:[now-6h%20TO%20now]&size=10000")
        baseUrl = (f"{self.serverBaseUrl}cicd-report-center/_search?q=pipeline.applicationArea:OSS%20BASE%20PLATFORM"
                   f"%20AND%20(pipeline.status:TERMINAL%20OR%20pipeline.status:SUCCEEDED)"
                   f"%20AND%20pipeline.endTime:[now-6h%20TO%20now]&size=10000")

        upgradeUrls = [relChildFlowUrl, prodUrl, stabilityUrl, releaseParentFlowlUrl, appUrl, baseUrl]
        indices = ["release-upgrade-install-data", "pso-upgrade-data",
                   "pe-stability-data", "release-upgrade-install-data",
                   "app-upgrade-install-data", "app-upgrade-install-data"]
        # Using dictionary comprehension to create the dictionary
        result_dict = {url: index for url, index in zip(upgradeUrls, indices)}
        logging.info(result_dict)
        pipelineIds = []
        for url, index in result_dict.items():
            pipelines = set(self.getPipelineIdList(url))
            es = ElasticSearchLib(self.username, self.password, index)
            for pipId in pipelines:
                if es.searchPipelineID(pipId, ""):
                    logging.info(f"Pipeline {pipId} is already registered in {index}!")
                else:
                    pipelineIds.append(pipId)
        return pipelineIds

    def getPipelineIdList(self, url):
        response = requests.get(url, auth=self.auth, verify=False)
        data = json.loads(response.text)
        pipelineIdList = []
        for hit in data['hits']['hits']:
            pipelineId = hit['_source']['pipeline']['id']
            pipelineIdList.append(pipelineId)
        return pipelineIdList

    def getUpgradeApplicationsData(self):
        pipelineIds = self.getUpgradePipelinesData()
        logging.info(f"Pipeline Ids to be Upgraded: {pipelineIds}")
        spinnaker = SpinnakerLib(self.username, self.password)
        for pipelineID in pipelineIds:
            pipelineData, csvData = spinnaker.getParameterValuesById(pipelineID)
            toBeUpdated = spinnaker._toExecutionUpgradeRecords(pipelineData, csvData)
            es = ElasticSearchLib(self.username, self.password, csvData.get("dataUploadIndex"))
            logging.info(f"Found {len(toBeUpdated)} executions from ElasticSearch")
            es.updateDocuments(toBeUpdated)
