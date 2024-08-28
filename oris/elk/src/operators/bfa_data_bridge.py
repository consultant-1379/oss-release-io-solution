''' importing logging, os, sys, argparse, time. module'''
import logging
import sys
from lib.elastic_lib import ElasticSearchLib
from lib.bfa_mongo_lib import MongoDB

logger = logging.getLogger(__name__)
username = "EIAPREG100"
password = "CztvYwveBHUp8A2UQtBxDxsB"


def setLogLevel(debug):
    log = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log,
        format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")


def getMongoData():
    es = ElasticSearchLib(username, password, "")
    indices = ["product-staging-data", "cicd-report-center", "eo-product-staging-data"]
    appData, productData, eoProduct = es.elasticData(indices)
    logger.info("\n\n-----------EIC APP Staging Failure Causes------------------")
    appMongoData = MongoDB.mongoData("", appData, "APP")
    pushData(appMongoData, "APP")
    logger.info("\n\n-----------EIC Product Staging Failure Causes------------------")
    prodMongoData = MongoDB.mongoData("", productData, "PROD")
    pushData(prodMongoData, "PROD")
    logger.info("\n\n-----------EO Product Staging Failure Causes------------------")
    eoProdMongoData = MongoDB.mongoData("", eoProduct, "eoPROD")
    pushData(eoProdMongoData, "EOPROD")


def pushData(exec, i):
    if i == "APP":
        es = ElasticSearchLib(username, password, "bfa-appstaging")
        es.updateDocuments(exec)
    elif i == "PROD":
        es = ElasticSearchLib(username, password, "bfa-productstaging")
        es.updateDocuments(exec)
    elif i == "EOPROD":
        es = ElasticSearchLib(username, password, "eo-bfa-productstaging")
        es.updateDocuments(exec)


def main() -> int:
    setLogLevel('debug')
    getMongoData()


if __name__ == '__main__':
    sys.exit(main())
