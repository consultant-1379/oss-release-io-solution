''' importing logging, ,sys, module'''
import json
import logging
import requests
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.spinnaker_lib import SpinnakerLib


class E2EDoraSetupMetrics():
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)

    def getPipelineIds(self):
        url = "https://elastic.hahn130.rnd.gic.ericsson.se/product-staging-data/_search?q=(pipeline.status:SUCCEEDED)%20AND\
            %20pipeline.endTime:%5Bnow-6h%20TO%20now%5D&size=10000"
        response = requests.get(url, auth=self.auth, verify=False)
        data = json.loads(response.text)
        pipeline_ids = []
        for hit in data['hits']['hits']:
            pipeline_id = hit['_source']['pipeline']['id']
            pipeline_ids.append(pipeline_id)
        pip_id = set(pipeline_ids)
        logging.info(f"Found {len(pip_id)} Product Staging Pipelines")
        logging.info(f"List of Pipeline ID's: {pip_id}")
        return pip_id

    def leadTimeCal(self):
        pipelineIds = self.getPipelineIds()
        spinnaker = SpinnakerLib(self.username, self.password)
        es = ElasticSearchLib(self.username, self.password, "eic-end-to-end-dora")
        pip_id = []
        for id in pipelineIds:
            release = spinnaker.releasePipelineCheck(id)
            if release is not True:
                pip_id.append(id)
        pipelineList = []
        for id in pip_id:
            parentID = spinnaker.getParentID(id)
            logging.info(f"Parent Pipeline id of Pipeline: {id} is {parentID}")
            checkApplication = spinnaker.appStagingCheck(parentID)
            adp = spinnaker.adpPipelineCheck(parentID)
            pipelineStatus = spinnaker.pipelineStatusCheck(parentID)
            if adp or pipelineStatus or checkApplication:
                pass
            else:
                pipelineList.append(parentID)
        logging.info(
            f"Found {len(pipelineList)} Product Staging Pipeline ID's triggered by Microservices")
        logging.info(f"List of Product Staging Pipeline ID's: {pipelineList}")
        for id in pipelineList:
            logging.info(f"Pipeline ID: {id}")
            if es.searchPipelineID(id, ""):
                logging.info(f"Pipeline {id} is already registered!")
            else:
                toBeUpdated = spinnaker.getPipelineRecord(id)
                logging.info(
                    f"Found {len(toBeUpdated)} executions from ElasticSearch")
                es.updateDocuments(toBeUpdated)
