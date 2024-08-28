"""Importing logging, os, requests, ndjson and datetime Modules"""
import logging
import requests
import os
import ndjson
from datetime import datetime


class DbAsCode:
    def __init__(self, username, password, seli_user, seli_pass, kibana_space, dashboard_type):
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)
        self.seliAuth = (seli_user, seli_pass)
        self.kibanaUrl = 'https://data-analytics-kibana.ews.gic.ericsson.se/s/test'
        self.headers = {
            "kbn-xsrf": "true",
        }
        self.dashboardType = dashboard_type
        self.kibanaSpace = kibana_space

    def checkCustomIdStatus(self, customId):
        url = f"{self.kibanaUrl}/api/saved_objects/dashboard/{customId}"
        response = requests.get(url, headers=self.headers, auth=self.auth, verify=False)
        if response.status_code == 200:
            self.exportNdJsonFile(customId)
        else:
            raise Exception('Invalid Custom ID Entered')

    def exportNdJsonFile(self, customId):
        export_url = f"{self.kibanaUrl}/api/saved_objects/_export"
        payload = {
            "objects": [
                {
                    "type": "dashboard",
                    "id": customId
                }
            ],
            "includeReferencesDeep": True
        }
        export_response = requests.post(export_url, headers=self.headers, json=payload, auth=self.auth, verify=False)
        if export_response.status_code == 200:
            with open(f"{customId}.ndjson", 'wb') as f:
                f.write(export_response.content)
            logging.info(f"Dashboard {customId} exported successfully.")
            self.updateNdJsonFile(customId)
        else:
            logging.info(f"Error exporting dashboard: {export_response.text}")

    def updateNdJsonFile(self, customId):
        file_path = f'./{customId}.ndjson'
        with open(file_path, 'r') as file:
            data = ndjson.load(file)
        dbCustomIds = {}
        for item in data:
            # Data view custom ID update
            types = ['index-pattern', 'search', 'visualization', 'lens']
            for kibanaType in types:
                if item.get('type') == kibanaType:
                    if kibanaType == 'index-pattern':
                        customValue = item['attributes']['title']
                        item['id'] = customValue.replace("test_", "")
                    self.checkCustomIDStatusAcrossSpaces(item['id'], item.get('type'))
                    if item.get("references") is not None:
                        for refID in item.get("references"):
                            refID['id'] = self.getReferencesData(refID, dbCustomIds)

            if item.get('type') == 'dashboard':
                if item['id'] != customId:
                    key = item['id']
                    customValue = item['attributes']['title']
                    item['id'] = customValue.replace(" ", "_")
                    dbCustomIds[key] = item['id']
                    self.checkCustomIDStatusAcrossSpaces(item['id'], item.get('type'))
                    if item.get("references") is not None:
                        for refID in item.get("references"):
                            refID['id'] = self.getReferencesData(refID, dbCustomIds)
                else:
                    customValue = item['attributes']['title']
                    item['id'] = customValue.replace(" ", "_")
                    self.checkCustomIDStatusAcrossSpaces(item['id'], item.get('type'))
                    # References Data view and Drilldown custom ID update
                    if item.get("references") is not None:
                        for refID in item.get("references"):
                            refID['id'] = self.getReferencesData(refID, dbCustomIds)

        logging.info("Dashboard ndjson file is Updated all custom_id's of the Dashboard and Index-Patterns")
        with open(file_path, 'w') as file:
            ndjson.dump(data, file)
            cur_date = datetime.now().strftime("%Y-%b-%d_%H:%M")
            artifactory_url = 'https://arm.seli.gic.ericsson.se/artifactory/'
            base_file_name = "DAK-NDJSON/" + cur_date + os.path.basename(file_path)
            requests.put("{0}/{1}/{2}".format(artifactory_url, "proj-eric-oss-ci-internal-generic-local",
                                              base_file_name), auth=self.seliAuth, verify=False,
                         data=open(file_path, 'rb'))
            ndjsonFilePath = artifactory_url + "proj-eric-oss-ci-internal-generic-local/DAK-NDJSON/"
            logging.info(f"Ndjson file is uploaded to: {ndjsonFilePath}")

    def getReferencesData(self, refID, dbCustomIds):
        if refID["type"] == "index-pattern":
            refID['id'] = refID["id"].replace('test_', '')
            return refID['id']
        elif refID["type"] == "dashboard":
            for key, value in dbCustomIds.items():
                if refID['id'] == key:
                    refID['id'] = value
                    return refID['id']
        else:
            return refID['id']

    def checkCustomIDStatusAcrossSpaces(self, customId, objectType):
        spaces = {'EIC': 'https://data-analytics-kibana.ews.gic.ericsson.se',
                  'EO': 'https://data-analytics-kibana.ews.gic.ericsson.se/s/eo',
                  'ESOA': 'https://data-analytics-kibana.ews.gic.ericsson.se/s/esoa',
                  'AUTO-APPS': 'https://data-analytics-kibana.ews.gic.ericsson.se/s/auto-apps',
                  'CICD': 'https://data-analytics-kibana.ews.gic.ericsson.se/s/cicd'
                  }
        customIdList = []
        for key in spaces.items():
            if self.dashboardType == "NEW":
                if self.kibanaSpace == key:
                    url = f"{spaces[key]}/api/saved_objects/{objectType}/{customId}"
                    response = requests.get(url, headers=self.headers, auth=self.auth, verify=False)
                    if response.status_code == 200:
                        raise Exception(
                            f"Custom ID: {customId} for type: {objectType} already exists in space {spaces[key]}")
            if self.dashboardType == "EXISTING":
                if self.kibanaSpace == key:
                    url = f"{spaces[key]}/api/saved_objects/{objectType}/{customId}"
                    response = requests.get(url, headers=self.headers, auth=self.auth, verify=False)
                    if response.status_code == 200:
                        logging.info(f"Custom ID:{customId} for type:{objectType} already exist in {spaces[key]}")
                    else:
                        customIdList.append(customId)
        if customIdList:
            for key in spaces.items():
                if key != self.kibanaSpace:
                    url = f"{spaces[key]}/api/saved_objects/{objectType}/{customId}"
                    response = requests.get(url, headers=self.headers, auth=self.auth, verify=False)
                    logging.info(f"Response code of custom ID: {response.status_code}")
                    if response.status_code == 200:
                        raise Exception(f"Custom ID:{customId} for type:{objectType} already exist in {spaces[key]}")
