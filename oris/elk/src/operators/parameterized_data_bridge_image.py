''' importing logging module'''
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.parameterized_spinnaker_lib import SpinnakerLib
from elk.src.operators.lib.csv_lib import csvData


class ParameterizedDoraSetup:
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
        spinnaker = SpinnakerLib(username, password)
        executions, index = spinnaker.getExecutionsById(id)
        if executions is not None and index is not None:
            es = ElasticSearchLib(self.username, self.password, index)
            toBeRegistered = []
            for exec in executions:
                if es.getDocumentById(exec["stage"]["id"]) is not None:
                    logging.warning(
                        f"WARNING: Stage {exec['stage']['id']} of Execution {id} is already registered!")
                    continue
                exec["pipeline"]["finished"] = False
                toBeRegistered.append(exec)
            es.updateDocuments(toBeRegistered)

    def __updateRegisteredExecutions__(self, username, password):
        spinnaker = SpinnakerLib(username, password)
        csvObj = csvData()
        indices = csvObj.getListOfIndices()
        for index in indices:
            es = ElasticSearchLib(self.username, self.password, index)
            logging.info("Finding unconcluded executions from Elastic Search")
            toBeUpdated = es.getUnfinishedDocuments()
            logging.info(
                f"Found {len(toBeUpdated)} pending execution stages from Elastic Search")
            pipelines = {}
            deletedPipelineID = []
            for execution in toBeUpdated:
                pipelineId = execution["pipeline"]["id"]
                if pipelineId not in pipelines:
                    checkPipelineIdData, index = spinnaker.getExecutionsById(pipelineId)
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
