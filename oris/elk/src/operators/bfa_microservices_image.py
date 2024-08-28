''' importing logging, os, sys, argparse, time. module'''
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.bfa_microservice_lib import MongoDataBase

logger = logging.getLogger(__name__)


class bfaDataBridge:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log,
            format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")

    def getMongoData(self):
        es = ElasticSearchLib(self.username, self.password, "bfa-microservices-data")
        mongoDB = MongoDataBase(self.username, self.password)
        path = '/usr/src/app/elk/src/etc/fem_list.properties'
        fems = []
        with open(path, 'r') as fp:
            fems = fp.readlines()
        for i in fems:
            fem = i.split(":")[0]
            femPort = i.replace("\n", "")
            mongoData, femUrl, faildbs = mongoDB.bfaData(femPort)
            newPipelineList = []
            for data in mongoData:
                pipelineName = data['projectName']
                buildNumber = data['buildNumber']
                id = pipelineName+"-"+str(buildNumber)
                result = es.searchPipelineID(id, fem)
                if not result:
                    newPipelineList.append(data)
            if newPipelineList:
                self.getJenkinsData(newPipelineList, femUrl, faildbs, es)

    def getJenkinsData(self, newPipelines, femUrl, faildb, es):
        mongoDB = MongoDataBase(self.username, self.password)
        records = mongoDB.getDataFromJenkins(newPipelines, femUrl, faildb)
        if records:
            es.updateDocuments(records)
