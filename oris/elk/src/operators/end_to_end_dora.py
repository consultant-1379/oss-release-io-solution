''' importing logging, ,sys, module'''
import json
import logging
import sys
import requests
from lib.elastic_lib import ElasticSearchLib
from lib.spinnaker_lib_dora import SpinnakerLib


username = "EIAPREG100"
password = "CztvYwveBHUp8A2UQtBxDxsB"
logger = logging.getLogger(__name__)


def setLogLevel(debug):
    log = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log,
        format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")


def getPipelineIds():
    url = "http://es.hahn051.rnd.gic.ericsson.se/product-staging-data/_search?q=pipeline.status:SUCCEEDED AND \
    pipeline.endTime:%5Bnow-6h TO now%5D&size=10000"
    response = requests.get(url)
    data = json.loads(response.text)
    pipeline_ids = []
    for hit in data['hits']['hits']:
        pipeline_id = hit['_source']['pipeline']['id']
        pipeline_ids.append(pipeline_id)
    pip_id = set(pipeline_ids)
    logger.info(f"Found {len(pip_id)} Product Staging Pipelines")
    logger.info(f"List of Pipeline ID's: {pip_id}")
    return pip_id


def leadTimeCal():
    pipelineIds = getPipelineIds()
    spinnaker = SpinnakerLib(username, password)
    es = ElasticSearchLib("", "", "eic-end-to-end-dora")
    pip_id = []
    for id in pipelineIds:
        release = spinnaker.releasePipelineCheck(id)
        if release is not True:
            pip_id.append(id)
    pipelineList = []
    for id in pip_id:
        parentID = spinnaker.getParentID(id)
        logger.info(f"Parent Pipeline id of Pipeline: {id} is {parentID}")
        checkApplication = spinnaker.appStagingCheck(parentID)
        adp = spinnaker.adpPipelineCheck(parentID)
        pipelineStatus = spinnaker.pipelineStatusCheck(parentID)
        if adp or pipelineStatus or checkApplication:
            pass
        else:
            pipelineList.append(parentID)
    logger.info(
        f"Found {len(pipelineList)} Product Staging Pipeline ID's triggered by Microservices")
    logger.info(f"List of Product Staging Pipeline ID's: {pipelineList}")
    for id in pipelineList:
        if es.searchPipelineID(id, ""):
            logger.info(f"Pipeline {id} is already registered!")
        else:
            toBeUpdated = spinnaker.getPipelineRecord(id)
            logger.info(
                f"Found {len(toBeUpdated)} executions from ElasticSearch")
            es.updateDocuments(toBeUpdated)


def main() -> int:
    setLogLevel('debug')
    leadTimeCal()


if __name__ == '__main__':
    sys.exit(main())
