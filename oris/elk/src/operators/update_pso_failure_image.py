"""Upgrade PSO Failures"""
import logging
import requests
from elk.src.operators.lib.elastic_lib import ElasticSearchLib


class ElasticQueryExecutor:
    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self.username = username
        self.password = password
        self.headers = {"Content-Type": "application/json"}
        self.auth = (username, password)
        self.serverBaseUrl = "https://elastic.hahn130.rnd.gic.ericsson.se/"
        self.index = "product-staging-failure-data"

    def executeElasticQuery(self):
        query = {
            "size": 10000,
            "query": {
                "bool": {
                    "must": [
                        {
                            "nested": {
                                "path": "jiraDetails",
                                "query": {
                                    "exists": {
                                        "field": "jiraDetails"
                                    }
                                }
                            }
                        },
                        {
                            "range": {
                                "pipeline.endTime": {
                                    "gte": "now-30d",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "_source": ["pipeline", "stage", "deploymentName", "jiraDetails"]
            }
        url = self.serverBaseUrl + "product-staging-data/_search"
        response = requests.post(url, headers=self.headers, json=query, auth=self.auth, verify=False)
        if response.status_code == 200:
            result = response.json()
            self.uploadDocuments(result)
        else:
            raise Exception("Error:", response.status_code, response.text)

    def uploadDocuments(self, data):
        if data.get('hits', {}).get('hits', []):
            for hit in data['hits']['hits']:
                stageId = hit['_source']['stage']['id']
                jiraDetailsList = hit['_source'].get('jiraDetails', [])
                es = ElasticSearchLib(self.username, self.password, self.index)
                for index, jira_detail in enumerate(jiraDetailsList):
                    documentId = f"{stageId}_{index}"
                    newDoc = {
                        "pipeline": hit['_source']['pipeline'],
                        "stage": hit['_source']['stage'],
                        "deploymentName": hit['_source'].get('deploymentName', "null"),
                        "jiraId": jira_detail.get('id', ""),
                        "jiraIssueCategory": jira_detail.get('category', ""),
                        "status": jira_detail.get('status', "")
                    }
                    es.postDocument(documentId, newDoc)
