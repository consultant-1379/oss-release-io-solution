''' importing logging, os, sys, argparse, time. module'''
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.bfa_mongo_lib import MongoDB


class bfaAppProdMetricsSetup():
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def getMongoData(self):
        es = ElasticSearchLib(self.username, self.password, "")
        indices = ["product-staging-data", "cicd-report-center", "eo-product-staging-data"]
        appData, productData, eoProduct = es.elasticData(indices)
        logging.info("\n\n-----------EIC APP Staging Failure Causes------------------")
        appMongoData = MongoDB.mongoData("", appData, "APP")
        self.pushData(appMongoData, "APP")
        logging.info("\n\n-----------EIC Product Staging Failure Causes------------------")
        prodMongoData = MongoDB.mongoData("", productData, "PROD")
        self.pushData(prodMongoData, "PROD")
        logging.info("\n\n-----------EO Product Staging Failure Causes------------------")
        eoProdMongoData = MongoDB.mongoData("", eoProduct, "eoPROD")
        self.pushData(eoProdMongoData, "EOPROD")

    def pushData(self, exec, i):
        if i == "APP":
            es = ElasticSearchLib(self.username, self.password, "bfa-appstaging")
            es.updateDocuments(exec)
        elif i == "PROD":
            es = ElasticSearchLib(self.username, self.password, "bfa-productstaging")
            es.updateDocuments(exec)
        elif i == "EOPROD":
            es = ElasticSearchLib(self.username, self.password, "eo-bfa-productstaging")
            es.updateDocuments(exec)
