'''Updating Duration of RPT Indices'''
from datetime import datetime, timedelta
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.time_lib import RPT


class rptDataBridge:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)

    def yesterday_date(self):
        yesterday = (datetime.today()-timedelta(days=1)).strftime('%Y.%m.%d')
        return yesterday

    def rptFunctions(self):
        index = "express-logs-"+self.yesterday_date()
        yesterday = (datetime.today()-timedelta(days=2)).strftime('%Y.%m.%d')
        pre_index = "express-logs-"+yesterday
        instance = ["https://elastic.hahn130.rnd.gic.ericsson.se/"]
        rpt = RPT()
        es_lib = ElasticSearchLib(self.username, self.password, index)
        for url in instance:
            mapping = rpt.rptMapping(index, es_lib, url)
            if mapping is True:
                statusRecords = rpt.rptStatus(es_lib, url)
                versionRecords = rpt.rptVersions(es_lib, url)
                status_es = ElasticSearchLib(self.username, self.password, "rpt-status")
                version_es = ElasticSearchLib(self.username, self.password, "rpt-versions")
                for doc in statusRecords:
                    id = doc["id"]
                    status_es.rptDocumentsCreate(doc, id, url)
                for doc in versionRecords:
                    id = doc["id"]
                    version_es.rptDocumentsCreate(doc, id, url)
                rpt.addingDuration(es_lib, url)
                rpt.firstDocDuration(index, es_lib, url)
                rpt.lastDocDuration(index, es_lib, url)
                rpt.addingEnvDocuments(index, pre_index, es_lib, url)
            else:
                self.logger.info("Mapping is not done")
