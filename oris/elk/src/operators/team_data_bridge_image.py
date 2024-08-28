''' importing logging, ,sys, module'''
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.csv_lib import csvData


class TeamsDataSetup():
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def getTeamsData(self):
        Team = csvData()
        jsonData = Team.readJsonData()
        logging.info(f"Teams Data pushed to elastic {jsonData}")
        self.pushData(jsonData)

    def pushData(self, exec):
        es = ElasticSearchLib(self.username, self.password, "teams-data")
        es.updateDocuments(exec)
