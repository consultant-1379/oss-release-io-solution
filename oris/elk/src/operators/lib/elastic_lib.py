'''import json logging module'''
import json
import logging
from datetime import date, datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from . import record_util


class ElasticSearchLib:

    def __init__(self, username, password, esindex):
        self._logger = logging.getLogger(__name__)
        self._username = username
        self._password = password
        self._auth = (self._username, self._password)
        self._index = esindex
        self._instances = ["https://elastic.hahn130.rnd.gic.ericsson.se/"]
        self._headers = {"Content-Type": "application/json"}

    def searchPipelineID(self, id, fem):
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                if fem != "":
                    url = f"{instance + self._index}/_search?q=pipeline.id.keyword:{id}" \
                        f"%20AND%20pipeline.fem.keyword:{fem}"
                else:
                    url = f"{instance + self._index}/_search?q=pipeline.id:{id}"
                result = session.get(url, verify=False).json()
            except ConnectionError:
                raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
            if result["hits"]["total"]["value"] != 0:
                self._logger.info(f"Found document with ID {id}")
                return True
            else:
                self._logger.info(f"Cannot find document with ID {id}")
                return False

    def getDocumentById(self, id):
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                result = session.get(f"{instance + self._index}/_doc/{id}", verify=False).json()
            except ConnectionError:
                raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
            if result["found"]:
                self._logger.debug(f"Found document with ID {id}")
                return result["_source"]
            else:
                self._logger.debug(f"Cannot find document with ID {id}")
                return None

    def getUnfinishedDocuments(self, start=0):
        size = 100
        if ("eiap-jira-center" in self._index or
                "eo-jira-center" in self._index or
                "esoa-jira-center" in self._index or
                "autoapps-jira-center" in self._index):
            query = {"size": size, "from": start, "query": {"query_string": {
                "query": "concluded:false"}}}
        else:
            query = {"size": size, "from": start, "query": {"query_string": {
                "query": "pipeline.finished:false OR stage.finished:false"}}}
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                response = session.get(f"{instance + self._index}/_search", json=query, verify=False)
                self._logger.debug(f"Search response: {response}\n{response.text}")
            except ConnectionError:
                raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
            self._logger.debug(f"Search response: {response}\n{response.text}")
            result = response.json()
            documents = []
            if result["hits"]["total"]["value"] > start + size:
                documents = documents + self.getUnfinishedDocuments(start + size)
            for exec in result["hits"]["hits"]:
                documents.append(exec["_source"])
            self._logger.debug(
                f"Found {len(documents)} unfinshed executions")
            return documents

    def updateDocuments(self, documents):
        indices = ["eiap-jira-center", "eo-jira-center",
                   "esoa-jira-center", "bfa-appstaging",
                   "bfa-productstaging", "eo-bfa-productstaging",
                   "autoapps-jira-center", "bfa-microservices-data",
                   "teams-data", "stability-stkpi-data"]
        count = 0
        c_counts = {}
        for doc in documents:
            data = json.dumps({
                "doc": doc,
                "doc_as_upsert": True
            }, default=self._json_serial)
            if self._index in indices:
                if "id" in doc:
                    docId = doc["id"]
                else:
                    pipeline_id = doc["pipeline"]["id"]
                    if pipeline_id not in c_counts:
                        c_counts[pipeline_id] = 0
                    docId = f"{pipeline_id}_{c_counts[pipeline_id]}"
                    c_counts[pipeline_id] += 1
            elif (self._index == "pso-upgrade-data" or self._index == "release-upgrade-install-data" or
                  self._index == "pe-stability-data" or self._index == "app-upgrade-install-data"):
                docId = doc["stage"]["id"] + "_" + str(count)
                count += 1
            else:
                docId = doc["stage"]["id"]
            if docId:
                self._logger.info(f"Document is updated in elastic search index '{self._index}' with ID : {docId}")
            for instance in self._instances:
                try:
                    session = requests.Session()
                    session.auth = self._auth
                    retry = Retry(total=10, connect=10, backoff_factor=1)
                    adapter = HTTPAdapter(max_retries=retry)
                    session.mount("https://", adapter)
                    response = session.post(instance + self._index + "/_update/" + docId,
                                            headers=self._headers, data=data, verify=False)
                except ConnectionError:
                    raise RuntimeError("Maximum attempts exceeded hence terminate the execution") from ConnectionError
                response.raise_for_status()
                self._logger.debug(
                    f"Successfully updated document with id {docId}")

    def postDocument(self, docId, document):
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                response = session.post(instance + self._index + "/_doc/" + docId,
                                        headers=self._headers, json=document, auth=self._auth, verify=False)
            except ConnectionError:
                raise RuntimeError("Maximum attempts exceeded hence terminate the execution") from ConnectionError
            response.raise_for_status()
            self._logger.debug(
                f"Successfully updated document with id {docId}")

    def updateDocumentConclusion(self, docId, getJiraType):
        doc = {"type": getJiraType, "comments": "Jira is Converted to " + getJiraType, "concluded": True}
        data = json.dumps({
            "doc": doc,
            "doc_as_upsert": True
        }, default=self._json_serial)
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                response = session.post(instance + self._index + "/_update/" + docId,
                                        headers=self._headers, data=data, verify=False)
            except ConnectionError:
                raise RuntimeError("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
            response.raise_for_status()
            self._logger.debug(
                f"Successfully updated {docId} document")

    def deleteDocument(self, jiraID):
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                response = session.delete(instance + self._index + "/_doc/" + jiraID,
                                          headers=self._headers, verify=False)
            except ConnectionError:
                raise RuntimeError("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
            response.raise_for_status()

    def _json_serial(self, obj):
        if isinstance(obj, (datetime, date)):
            return int(datetime.timestamp(obj) * 1000)
        raise TypeError(f"Type {type(obj)} not serializable")

    def elasticData(self, indices):
        app = []
        product = []
        eoProduct = []
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            for index in indices:
                url = (
                    f"{self._instances[0] + index}/_search?q="
                    "(pipeline.status:SUCCEEDED%20OR%20TERMINAL)%20AND%20"
                    "(stage.status:FAILED_CONTINUE%20OR%20TERMINAL)%20AND%20"
                    "pipeline.endTime:[now-2h%20TO%20now]&size=10000")
                result = session.get(url, verify=False).json()
                indexData = []
                for re in result["hits"]["hits"]:
                    if re["_source"]["stage"]["status"] != "SUCCEEDED":
                        if re["_source"]["stage"]["jobUrl"] is not None:
                            indexData.append(re)
                for data in indexData:
                    exec = record_util.bfaFailureCausesData()
                    exec["pipeline"]["id"] = data["_source"]["pipeline"]["id"]
                    exec["pipeline"]["status"] = data["_source"]["pipeline"]["status"]
                    exec["pipeline"]["application"] = data["_source"]["pipeline"]["application"]
                    exec["pipeline"]["name"] = data["_source"]["pipeline"]["name"]
                    exec["pipeline"]["url"] = data["_source"]["pipeline"]["url"]
                    exec["pipeline"]["startTime"] = data["_source"]["pipeline"]["startTime"]
                    exec["pipeline"]["endTime"] = data["_source"]["pipeline"]["endTime"]
                    exec["pipeline"]["duration"] = data["_source"]["pipeline"]["duration"]
                    exec["stage"]["id"] = data["_source"]["stage"]["id"]
                    exec["stage"]["name"] = data["_source"]["stage"]["name"]
                    exec["stage"]["status"] = data["_source"]["stage"]["status"]
                    exec["stage"]["jobUrl"] = data["_source"]["stage"]["jobUrl"]
                    exec["stage"]["jobName"] = data["_source"]["stage"]["jobUrl"].split("/")[-3]
                    exec["stage"]["buildNumber"] = int(data["_source"]["stage"]["jobUrl"].split("/")[-2])
                    exec["stage"]["jobFullDisplayName"] = data["_source"]["stage"]["jobFullDisplayName"]
                    exec["stage"]["startTime"] = data["_source"]["stage"]["startTime"]
                    exec["stage"]["endTime"] = data["_source"]["stage"]["endTime"]
                    exec["stage"]["duration"] = data["_source"]["stage"]["duration"]
                    if (index == "product-staging-data"):
                        product.append(exec)
                    elif (index == "eo-product-staging-data"):
                        eoProduct.append(exec)
                    else:
                        app.append(exec)
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        return app, product, eoProduct

    def rptEnvironments(self, index, url):
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            result = session.get(f"{url + index}/_search?q=old.0.name:*&size=10000", verify=False).json()
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        record = []
        if result["hits"]["total"]["value"] != 0:
            for i in result["hits"]["hits"]:
                record.append(i)
        else:
            self._logger.debug("Can not find documents")
        environments = []
        for rec in record:
            environments.append(rec["_source"]["old"]["0"]["name"])
        return list(set(environments))

    def rptUpdateDocument(self, status, duration, id, url):
        if (status == "Standby"):
            doc = {"standby_duration": duration}
        elif (status == "Available"):
            doc = {"available_duration": duration}
        elif (status == "Refreshing"):
            doc = {"refreshing_duration": duration}
        elif (status == "Quarantine"):
            doc = {"quarantine_duration": duration}
        elif (status == "Reserved"):
            doc = {"reserved_duration": duration}
        data = json.dumps({
            "doc": doc,
            "doc_as_upsert": True
        }, default=self._json_serial)
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            response = session.post(url + self._index + "/_update/" + id,
                                    headers=self._headers, data=data, verify=False)
            self._logger.debug(f"Search response: {response}\n")
        except ConnectionError:
            raise RuntimeError("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        self._logger.debug(
            f"Successfully updated {id} document")

    def getStatusDoc(self, statusName, url, start=0):
        size = 10000
        query = {"size": size, "from": start, "query": {"bool": {"must": [{"match": {"old.0.status": statusName}}]}}}
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            response = session.get(f"{url + self._index}/_search", json=query, verify=False)
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        result = response.json()
        record = []
        if result["hits"]["total"]["value"] != 0:
            for i in result["hits"]["hits"]:
                record.append(i)
        else:
            self._logger.debug("Cannot find documents")
        statusData = []
        for rec in record:
            statusData.append(rec)
        return statusData

    def rptDocDuration(self, index, statusName, envName, url):
        start, size = 0, 10000
        query = {"size": size, "from": start, "query": {"bool": {"must": [{"match": {"old.0.status": statusName}},
                                                                          {"match": {"old.0.name": envName}}]}}}
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            response = session.get(f"{url + index}/_search", json=query, verify=False)
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        result = response.json()
        record = []
        if result["hits"]["total"]["value"] != 0:
            for i in result["hits"]["hits"]:
                record.append(i)
        else:
            self._logger.debug("Cannot find documents")
        envStatusData = []
        for rec in record:
            if rec["_source"]["old"]["0"]["name"] == envName:
                envStatusData.append(rec)
        return envStatusData

    def rptDocumentsCreate(self, doc, id, url):
        data = json.dumps(doc, default=str)
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            response = session.post(url + self._index + "/_doc/" + id,
                                    headers=self._headers, data=data, verify=False)
            self._logger.debug(f"Search response: {response}\n")
        except ConnectionError:
            raise RuntimeError("Maximum attempts exceeded hence terminate the execution") from ConnectionError
        self._logger.debug(
            f"Successfully created document with id {id}")

    def rptMappingLimit(self, index, url):
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            settings_body = {"index.mapping.total_fields.limit": 2000}
            session.mount("https://", adapter)
            result = session.put(f"{url + index}/_settings", json=settings_body, verify=False)
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        return result

    def rmvRPTDoc(self, url):
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            response = session.get(f"{url + self._index}/_search?q=old.0.name:*&size=10000", verify=False)
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        result = response.json()
        record = []
        if result["hits"]["total"]["value"] != 0:
            for i in result["hits"]["hits"]:
                record.append(i)
        else:
            self._logger.debug("Cannot find documents")
        for rec in record:
            id = rec["_id"]
            if(id.__contains__("-regulus") or id.__contains__("-envReg")):
                print(id)
                self.deleteDocument(id)

    def createIndexMapping(self, mapping):
        indexName = self._index
        url = f'{self._instances[0]}{indexName}'
        response = requests.get(url, auth=self._auth, verify=False)
        if response.status_code != 200:
            response = requests.put(url, auth=self._auth, verify=False,
                                    data=json.dumps(mapping), headers={'Content-Type': 'application/json'},)
            if response.status_code == 200:
                self._logger.info(f"Index '{indexName}' is created with mapping.")
            else:
                raise IndexError(f'Failed to create index due to mapping format. Response: {response.text}')

    def CreateDataView(self, index, time_field, custom_data_view_id):
        headers = {'kbn-xsrf': 'true', 'Content-Type': 'application/json'}
        kibana_url = "https://data-analytics-kibana.ews.gic.ericsson.se/s/test"
        url = f'{kibana_url}/api/saved_objects/index-pattern/{custom_data_view_id}'
        data = {
            "attributes": {
                "title": index,
                "timeFieldName": time_field
            }
        }
        response = requests.get(url, headers=headers, auth=self._auth, verify=False)
        if response.status_code == 200:
            self._logger.info(f"Data view with customID '{custom_data_view_id}' already exists.")
        else:
            response = requests.post(url, headers=headers, data=json.dumps(data), auth=self._auth, verify=False)
            if response.status_code == 200:
                self._logger.info(f"Data View '{index}' with customID '{custom_data_view_id}' "
                                  f"is created.")
            else:
                raise ConnectionError(f'Failed to create Data View. Response: {response.text}')

    def getExistIndexMapping(self, index):
        indexName = self._index
        url = f'{self._instances[0]}{indexName}'
        response = requests.get(url, auth=self._auth, verify=False)
        if response.status_code == 200:
            mapping = response.json()
            if mapping[index]['mappings']:
                self._logger.info("Index already exists with mapping.")
                return {"mappings": mapping[index]['mappings']}
            else:
                self._logger.warning((f"index '{index}' is already created manually in UI without mapping"))
                response = requests.delete(url, auth=self._auth, verify=False)
                if response.status_code == 200:
                    self._logger.info(f"Manually created index '{index}' is deleted successfully.")
                    return []
                else:
                    raise ConnectionError(f"Failed to delete index. Status code: {response.status_code}")
        else:
            return []

    def getPipelineDetails(self, index, startTime, endTime, skipChart, tag, value):
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            for idx in index:
                baseUrl = f"{self._instances[0] + idx}/_search?q="
                query = [
                    "(pipeline.status:SUCCEEDED%20OR%20TERMINAL)",
                    f"(pipeline.{tag}:{value})",
                    f"pipeline.endTime:[{startTime}%20TO%20{endTime}]"
                ]
                if skipChart is not None and skipChart.strip() != "":
                    query.append(f"(pipeline.skipChartRelease:{skipChart})")
                url = baseUrl + "%20AND%20".join(query) + "&size=10000"
                response = session.get(url, verify=False).json()
            return response
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError

    def getPipelineChartNames(self, index, startTime, endTime, skipChart, tag, value):
        response = self.getPipelineDetails(index, startTime, endTime, skipChart, tag, value)
        dic = {}
        if isinstance(response, dict) and "hits" in response:
            for re in response["hits"]["hits"]:
                status = re["_source"]["pipeline"]["status"]
                if status in ("TERMINAL", "SUCCEEDED"):
                    pipelineData = re["_source"]["pipeline"]
                    chartNames = pipelineData["chartName"]
                    pipelineName = pipelineData["name"]
                    if pipelineName not in dic:
                        chart_set = set([chartNames]) if isinstance(chartNames, str) else set(chartNames)
                        dic[pipelineName] = chart_set
                    else:
                        if isinstance(chartNames, list):
                            dic[pipelineName].update(chartNames)
                        else:
                            dic[pipelineName].add(chartNames)
            for key in dic:
                dic[key] = list(dic[key])
        return dic

    def getPipelineData(self, index, pipelineName, chartName, startTime, endTime, skipChart, tag, value):
        response = self.getPipelineDetails(index, startTime, endTime, skipChart, tag, value)
        try:
            if 'hits' in response:
                records = list(response['hits']['hits'])
                hasStage = any(record['_source']['stage']['name'] == "Fetch Build Upload Release"
                               for record in records if record['_source']['pipeline']['name'] == pipelineName and
                               record['_source']['pipeline']['chartName'] == chartName)
                uniqueRecords = list({
                    f"{record['_source']['pipeline']['chartName']}-"
                    f"{record['_source']['pipeline']['id']}-"
                    f"{record['_source']['pipeline']['status']}": record
                    for record in records
                    if record['_source']['pipeline']['name'] == pipelineName and
                    record['_source']['pipeline']['chartName'] == chartName and
                    (not hasStage or record['_source']['stage']['name'] == "Fetch Build Upload Release")
                }.values())
            else:
                return []
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        record = sorted(
            uniqueRecords,
            key=lambda x: (
                x["_source"]["pipeline"]["startTime"],
                x["_source"]["pipeline"]["endTime"]
            )
        )
        return record

    def getMttrConclusion(self, indices):
        record = []
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            for index in indices:
                url = f"{self._instances[0] + index}/_search?q=" \
                    f"(pipeline.conclusion:false)&size=10000"
                response = session.get(url, verify=False).json()
                for re in response["hits"]["hits"]:
                    record.append(re)
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        return record

    def updateMTTRDocuments(self, documents):
        for doc in documents:
            self._logger.debug(f"Successfully updated document with id {doc}")
            data = json.dumps({
                "doc": doc,
                "doc_as_upsert": True
            }, default=self._json_serial)
            if "pipeline" in doc and "id" in doc["pipeline"]:
                docId = doc["pipeline"]["id"]
            if docId:
                self._logger.info(f"Executing for Document ID : {docId}")
            for instance in self._instances:
                try:
                    session = requests.Session()
                    session.auth = self._auth
                    retry = Retry(total=10, connect=10, backoff_factor=1)
                    adapter = HTTPAdapter(max_retries=retry)
                    session.mount("https://", adapter)
                    response = session.post(instance + self._index + "/_update/" + docId,
                                            headers=self._headers, data=data, verify=False)
                except ConnectionError:
                    raise RuntimeError("Maximum attempts exceeded hence terminate the execution") from ConnectionError
                response.raise_for_status()
                self._logger.debug(
                    f"Successfully updated document with id {docId}")

    def deletePipelineData(self, pipelineID):
        query = {"query": {"match": {"pipeline.id.keyword": pipelineID}}}
        for instance in self._instances:
            try:
                session = requests.Session()
                session.auth = self._auth
                retry = Retry(total=10, connect=10, backoff_factor=1)
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                response = session.post(instance + self._index + "/_delete_by_query",
                                        headers=self._headers, verify=False, json=query)
            except ConnectionError:
                raise RuntimeError("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
            response.raise_for_status()

    def getProdMTTRPipelineDetails(self, index, startTime, endTime, skipChart, tag, value):
        try:
            session = requests.Session()
            session.auth = self._auth
            retry = Retry(total=10, connect=10, backoff_factor=1)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            for idx in index:
                baseUrl = f"{self._instances[0] + idx}/_search?q="
                query = [
                    f"(pipeline.{tag}:{value})",
                    f"pipeline.endTime:[{startTime}%20TO%20{endTime}]"
                ]
                startDate = datetime.fromisoformat(startTime.replace("Z", "+00:00"))
                endDate = datetime.strptime(endTime, "%Y-%m-%dT%H:%M:%S.%f%z")
                endTime = endDate.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                endDate = datetime.fromisoformat(endTime.replace("Z", "+00:00"))
                if startDate.weekday() < 5 and endDate.weekday() < 5:
                    query.insert(0, "(pipeline.status:SUCCEEDED%20OR%20TERMINAL)")
                else:
                    query.insert(0, "pipeline.status:SUCCEEDED")
                if skipChart is not None and skipChart.strip() != "":
                    query.append(f"(pipeline.skipChartRelease:{skipChart})")
                url = baseUrl + "%20AND%20".join(query) + "&size=10000"
                response = session.get(url, verify=False).json()
                if 'hits' in response:
                    records = list(response['hits']['hits'])
                    uniqueRecords = list({
                        f"{record['_source']['pipeline']['id']}": record
                        for record in records
                    }.values())
                else:
                    return []
        except ConnectionError:
            raise Exception("Maximum attempts are exceeded hence terminating the execution") from ConnectionError
        record = sorted(
            uniqueRecords,
            key=lambda x: (
                x["_source"]["pipeline"]["startTime"],
                x["_source"]["pipeline"]["endTime"]
            )
        )
        return record
