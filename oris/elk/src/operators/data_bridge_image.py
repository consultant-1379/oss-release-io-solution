''' importing logging module'''
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.spinnaker_lib import SpinnakerLib


class DoraMetricsSetup:
    """
    Helps register and scan DORA metrics
    """

    def __init__(self, username, password, exec_type, exec_id):
        self.username = username
        self.password = password
        self.exec_type = exec_type
        self.exec_id = exec_id

    def executor(self):
        if 'Register' in self.exec_type:
            self.__registerNewExecution__(self.exec_id, self.username, self.password)
        elif 'Scan' in self.exec_type:
            self.__updateRegisteredExecutions__(self.username, self.password)
        else:
            raise Exception("Operations Failed")

    def __registerNewExecution__(self, id, username, password):
        logging.info(f"Registering execution with ID {id}")
        logging.info("Get execution details from Spinnaker")
        spinnaker = SpinnakerLib(username, password)
        executions = spinnaker.getExecutionsById(id)
        es = ElasticSearchLib(self.username, self.password, "")
        toBeRegistered = []
        for exec in executions:
            if exec["pipeline"]["rcrTag"] == "Product_Staging":
                es = ElasticSearchLib(self.username, self.password, "product-staging-data")
            elif exec["pipeline"]["rcrTag"] == "App_Staging":
                es = ElasticSearchLib(self.username, self.password, "cicd-report-center")
            elif exec["pipeline"]["rcrTag"] == "PE_Delivery_Staging":
                # temporary fix until PE Stability tag is rolled out to live
                if exec["pipeline"]["name"] == "automated-continuous-testing":
                    es = ElasticSearchLib(self.username, self.password, "pe-stability-staging-data")
                else:
                    es = ElasticSearchLib(self.username, self.password, "pe-delivery-staging-data")
            elif exec["pipeline"]["rcrTag"] == "PE_Stability_Testing":
                es = ElasticSearchLib(self.username, self.password, "pe-stability-staging-data")
            elif exec["pipeline"]["rsrTag"]:
                es = ElasticSearchLib(self.username, self.password,  "release-staging-data")
            elif exec["pipeline"]["rcrTag"] == "AutoApp_Staging":
                es = ElasticSearchLib(self.username, self.password,  "autoapp-staging-data")
            elif exec["pipeline"]["rcrTag"] == "AutoApp_Release":
                es = ElasticSearchLib(self.username, self.password,  "autoapps-release-staging")
            elif exec["pipeline"]["rcrTag"] == "AutoApp_BUR":
                es = ElasticSearchLib(self.username, self.password,  "autoapps-bur-data")
            elif exec["pipeline"]["rcrTag"] == "EO_APP_Staging":
                es = ElasticSearchLib(self.username, self.password,  "eo-app-staging-data")
            elif exec["pipeline"]["rcrTag"] == "EO_PROD_Staging":
                es = ElasticSearchLib(self.username, self.password,  "eo-product-staging-data")
            elif exec["pipeline"]["rcrTag"] == "EO_Product_E2E_Testing":
                es = ElasticSearchLib(self.username, self.password,  "eo-product-e2e-testing-data")
            elif exec["pipeline"]["esoaTag"] == "ESOA_App_Staging":
                es = ElasticSearchLib(self.username, self.password,  "esoa-app-staging-data")
            elif exec["pipeline"]["esoaTag"] == "ESOA_Product_Staging":
                es = ElasticSearchLib(self.username, self.password,  "esoa-product-staging-data")
            else:
                es = ElasticSearchLib(self.username, self.password,  "cicd-report-center")
            if es.getDocumentById(exec["stage"]["id"]) is not None:
                logging.warning(
                    f"Error: Stage {exec['stage']['id']} of Execution {id} is already registered!")
                continue
            # This is to frce this execution to be reprocessed during scanning
            exec["pipeline"]["finished"] = False
            toBeRegistered.append(exec)

        logging.info("Register stages in execution into ElasticSearch")
        es.updateDocuments(toBeRegistered)

    def __updateRegisteredExecutions__(self, username, password):
        spinnaker = SpinnakerLib(username, password)
        indices = [
            "product-staging-data",
            "autoapp-staging-data",
            "eo-app-staging-data",
            "eo-product-staging-data",
            "cicd-report-center",
            "esoa-app-staging-data",
            "esoa-product-staging-data",
            "pe-delivery-staging-data",
            "pe-stability-staging-data",
            "autoapps-release-staging",
            "autoapps-bur-data",
            "release-staging-data",
            "eo-product-e2e-testing-data"
        ]
        for index in indices:
            es = ElasticSearchLib(self.username, self.password, index)
            logging.info(f"Index pattern is: {index}")
            logging.info("Finding unconcluded executions from ElasticSearch")
            toBeUpdated = es.getUnfinishedDocuments()
            logging.info(
                f"Found {len(toBeUpdated)} pending execution stages from ElasticSearch")
            pipelines = {}
            deletedPipelineID = []
            for execution in toBeUpdated:
                pipelineId = execution["pipeline"]["id"]
                if pipelineId not in pipelines:
                    checkPipelineIdData = spinnaker.getExecutionsById(pipelineId)
                    if checkPipelineIdData:
                        pipelines[pipelineId] = checkPipelineIdData
                    else:
                        pipelines[pipelineId] = []
                        deletedPipelineID.append(pipelineId)
                updated = next((x for x in pipelines[pipelineId] if x["stage"]["id"] == execution["stage"]["id"]), None)
                if updated is None:
                    continue
                execution["pipeline"] = updated["pipeline"]
                execution["stage"] = updated["stage"]
                if execution["stage"]["id"] is not None:
                    if execution["stage"]["name"] == "Check is App Blocked" and \
                            execution["stage"]["status"] == "STOPPED":
                        updated["pipeline"]["status"] = "BLOCKED"
            logging.info("Execution status updated from Spinnaker")
            logging.info(f"Updating {len(toBeUpdated)} documents in ElasticSearch")
            es.updateDocuments(toBeUpdated)
            if deletedPipelineID:
                logging.info(f"Deleted spinnaker pipeline IDs: {deletedPipelineID}")
                for eachID in list(set(deletedPipelineID)):
                    es.deletePipelineData(eachID)
