"""import datetime module"""
import datetime
import logging
import requests
from elk.src.operators.lib.csv_lib import csvData
from elk.src.operators.lib.json_lib import jsonData


class SpinnakerLib:

    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self._username = username
        self._password = password
        self._auth = (username, password)
        self._serverBaseUrl = "https://spinnaker-api.rnd.gic.ericsson.se"

    def _toExecutionRecords(self, exec):
        try:
            self._logger.debug("Parsing execution: " + exec["id"])
        except KeyError:
            return [], ""
        csvObj = csvData()
        pr = {}
        pr["id"] = exec["id"]
        pr["status"] = exec["status"]
        pr["finished"] = exec["status"] not in ["RUNNING"]
        pr["application"] = exec["application"]
        pr["name"] = exec["name"]
        pr["url"] = f"{self._serverBaseUrl}/#/applications/{exec['application']}/executions/details/{exec['id']}"
        tagName = csvObj.getTagName(exec, "data_source")
        tagValue = self._getValue(exec, f"trigger.parameters.{tagName}", "")
        if tagValue in ["App_Staging", "AutoApp_Staging"]:
            tagAlias, index, pipelineJsonPath, stageJsonPath, dataPath = csvObj.getCsvTagsData(tagValue)
            pr[tagAlias] = tagValue
            startTimeStamp = self._getValue(exec, "startTime", exec["buildTime"])
            pr["startTime"] = self._parseTimeStamp(startTimeStamp)
            stageParameters = {}
            if pr["finished"]:
                pr, stageParameters = self.getParameterValues(exec, pr, pipelineJsonPath, stageJsonPath, dataPath)
            if "skipChartRelease" in pr and pr["skipChartRelease"] != "":
                pr["chartRelease"] = self._toSkipChartRelease(pr["skipChartRelease"])
            stages = []
            for stage in exec["stages"]:
                stages.append(self._toStageRecord(stage, stageParameters))
            records = []
            for sr in stages:
                record = {}
                record["pipeline"] = pr
                record["stage"] = sr
                records.append(record)
            return records, index
        else:
            return None, None

    def getParameterValues(self, exec, pr, pipelineJsonPath, stageJsonPath, dataPath):
        jsonFun = jsonData()
        csvObj = csvData()
        pipelineParameters = jsonFun.getParametersFromJson(pipelineJsonPath, dataPath, "pipeline")
        stageParameters = jsonFun.getParametersFromJson(stageJsonPath, dataPath, "stage")
        if pipelineParameters:
            applicationArea, appAlias = csvObj.getAppData(pr["application"])
            if applicationArea and appAlias:
                pr["applicationArea"] = applicationArea
                pr["appAlias"] = appAlias
            for k, v in pipelineParameters.items():
                value = self._getValue(exec, f"{v['path']}.{v['spinnakerParameter']}", "")
                if value:
                    pr[k] = value
            if "intChartName" in pr:
                chartNameList = str(pr["intChartName"]).replace(" ", "").split(",")
                pr["intChartName"] = chartNameList
                subApp = csvObj.getSubAppName(pr["intChartName"])
                if subApp and "appAlias" in pr:
                    pr["appAlias"] = subApp
                    pr["subApplication"] = subApp
            if "appChartName" in pr:
                chartNameList = str(pr["appChartName"]).replace(" ", "").split(",")
                pr["appChartName"] = chartNameList
            if exec["trigger"]["type"] == "manual":
                pr["service"] = "(Manual)"
                pr["buildNumber"] = -1
                pr["retrigger"] = False
            elif exec["trigger"]["type"] == "cron":
                pr["service"] = "(Scheduled)"
                pr["buildNumber"] = -1
                pr["retrigger"] = False
            elif exec["trigger"]["type"] == "pipeline":
                pr["service"] = exec["trigger"]["parentExecution"]["name"]
                pr["buildNumber"] = self._getValue(
                    exec, "trigger.parentExecution.trigger.buildNumber", -1)
                # To check if this is a retriggered execution,
                # check if restartDetails is present in the stage triggering this execution in parent pipeline
                parentPipelineStage = next(s for s in exec["trigger"]["parentExecution"]["stages"]
                                           if s["id"] == exec["trigger"]["parentPipelineStageId"])
                pr["retrigger"] = "restartDetails" in parentPipelineStage["context"]
            elif exec["trigger"]["type"] == "jenkins":
                pr["service"] = f"{exec['trigger']['master']},{exec['trigger']['job']}"
                pr["buildNumber"] = exec["trigger"]["buildNumber"]
                pr["retrigger"] = False
            if "chartName" not in pr:
                chartName = self._getValue(exec, "trigger.parameters.APP_NAME", "")
                if chartName:
                    pr["chartName"] = chartName
            if pr["service"] == "IDUN-PRODUCT-release-E2E-Flow":
                pr["chartName"] = "eic_helm_cr"
            if pr["service"] == "deployment-manager-submit-flow-integration-E2E-Flow":
                pr["chartName"] = "deploy-mgr-cr"
            startTimeStamp = self._getValue(exec, "startTime", exec["buildTime"])
            pr["startTime"] = self._parseTimeStamp(startTimeStamp)
            endTimeStamp = self._getValue(exec, "endTime", None)
            pr["endTime"] = self._parseTimeStamp(endTimeStamp)
            pr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
            pr["week"] = None
            if endTimeStamp:
                pr["week"] = self._getWeekNumber(endTimeStamp)
        return pr, stageParameters

    def _toStageRecord(self, stage, stageParameters):
        sr = {}
        sr["id"] = stage["id"]
        sr["name"] = stage["name"]
        sr["type"] = stage["type"]
        sr["finished"] = self._isFinished(stage["status"])
        sr["status"] = stage["status"]
        sr["passed"] = self._isPassed(sr["status"])
        startTimeStamp = self._getValue(stage, "startTime", None)
        sr["startTime"] = self._parseTimeStamp(startTimeStamp)
        if sr["type"] == "pipeline":
            sr["jobUrl"] = self._getValue(stage, "outputs.buildInfo.url", None)
        else:
            sr["jobUrl"] = self._getValue(stage, "context.buildInfo.url", None)
        if stageParameters:
            for k, v in stageParameters.items():
                value = self._getValue(stage, f"{v['path']}.{v['spinnakerParameter']}", None)
                if value:
                    sr[k] = value
            endTimeStamp = self._getValue(stage, "endTime", None)
            sr["endTime"] = self._parseTimeStamp(endTimeStamp)
            sr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        if "deploymentName" in sr and sr["deploymentName"] is not None:
            sr["deploymentName"] = sr["deploymentName"].split('_')[0]

        # Check if stage was restarted
        if sr["finished"] and sr["passed"] and "restartDetails" in stage["context"]:
            previousBuildResult = self._getValue(
                stage, "context.restartDetails.previousBuildInfo.result", None)
            previousExecId = self._getValue(
                stage, "context.restartDetails.previousException.source.executionId", None)
            if previousBuildResult is not None and not self._isPassed(previousBuildResult):
                # Previous execution failed, so consider this stage failed
                sr["passed"] = False
                sr["status"] = previousBuildResult
                sr["jobUrl"] = self._getValue(
                    stage, "context.restartDetails.previousBuildInfo.url", None)
                sr["jobFullDisplayName"] = self._getValue(
                    stage, "context.restartDetails.previousBuildInfo.fullDisplayName", None)
            elif stage["type"] == "pipeline" and previousExecId:
                childPipelineExecs = self.getExecutionsById(previousExecId)
                if not childPipelineExecs[0]["pipeline"]["passed"]:
                    sr["status"] = childPipelineExecs[0]["pipeline"]["status"]
                    sr["jobUrl"] = childPipelineExecs[0]["pipeline"]["url"]
                    sr["jobFullDisplayName"] = childPipelineExecs[0]["pipeline"]["name"]
                    sr["passed"] = False
            else:
                # This can be discussed.
                # If stage was restarted but there was no result from original execution,
                # should we fail this stage anyway?
                sr["status"] = "(Missing)"
                sr["jobUrl"] = None
                sr["jobFullDisplayName"] = None
                sr["passed"] = False
        return sr

    def _toSkipChartRelease(self, skipChartRelease):
        skipChartRelease = str(skipChartRelease).lower()
        value = ""
        if skipChartRelease == "false":
            value = "Deliverable Runs"
        elif skipChartRelease == "true":
            value = "Non-Deliverable Runs"
        else:
            value = "SkipChartRelease is Empty"
        return value

    def _isPassed(self, status):
        return status in ["SUCCEEDED", "SKIPPED", "NOT_STARTED", "RUNNING", "SUCCESS", "PAUSED"]

    def _isFinished(self, status):
        return status not in ["RUNNING", "PAUSED"]

    def _parseTimeStamp(self, timeStamp):
        return None if timeStamp is None else datetime.datetime.fromtimestamp(timeStamp / 1000)

    def _getWeekNumber(self, endTimeStamp):
        return None if (endTimeStamp is None) else datetime.datetime.fromtimestamp(endTimeStamp / 1000).isocalendar()[1]

    def _getDuration(self, timeStampStart, timeStampEnd):
        return None if (timeStampStart is None or timeStampEnd is None) else int(timeStampEnd - timeStampStart)

    def _getValue(self, data, path: str, default=Exception()):
        p = path.split(".")
        value = data
        for i, node in enumerate(p):
            if isinstance(value, list):
                # If the value is a list, iterate over each item
                return self._getValue(value[0], '.'.join(p[i:]), default) if value else default
            if node in value:
                value = value[node]
            elif isinstance(default, Exception):
                raise Exception(path + " not found in data: " + str(data))
            else:
                return default
        return value

    def getExecutionsById(self, id):
        queryUrl = self._serverBaseUrl + "/pipelines/" + id
        response = requests.get(queryUrl, auth=self._auth)
        self._logger.info(f"Executing for Pipeline ID: {id}")
        return self._toExecutionRecords(response.json())
