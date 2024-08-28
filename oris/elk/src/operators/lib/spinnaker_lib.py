"""import datetime module"""
import datetime
import logging
import requests
import re
from . import record_util
from elk.src.operators.lib.team_lib import TeamLib
from elk.src.operators.lib.time_utils import TimeCalculator
from elk.src.operators.lib.csv_lib import csvData


class SpinnakerLib:

    def __init__(self, username, password):
        self._logger = logging.getLogger(__name__)
        self._username = username
        self._password = password
        self._auth = (username, password)
        self._serverBaseUrl = "https://spinnaker-api.rnd.gic.ericsson.se"

    def _toPipelineRecords(self, exec):
        self._logger.debug("Parsing execution: " + exec["id"])
        pr = record_util.newE2EDoraPipelineData()
        pr["id"] = exec["id"]
        pr["status"] = exec["status"]
        pr["finished"] = exec["status"] not in ["RUNNING"]
        pr["application"] = exec["application"]
        pr["name"] = exec["name"]
        pr["url"] = f"{self._serverBaseUrl}/#/applications/{exec['application']}/executions/details/{exec['id']}"
        pr["chartName"] = self._getValue(
            exec, "trigger.parameters.CHART_NAME", "")
        if not pr["chartName"]:
            pr["chartName"] = self._getValue(exec, "trigger.parameters.APP_NAME", "")
            if not pr["chartName"]:
                pr["chartName"] = ""
        pr["chartVersion"] = self._getValue(
            exec, "trigger.parameters.CHART_VERSION", "")
        if not pr["chartVersion"]:
            pr["chartVersion"] = self._getValue(exec, "trigger.parameters.INT_CHART_VERSION", "")
            if not pr["chartVersion"]:
                pr["chartVersion"] = ""
        pr["skipChartRelease"] = self._getValue(
            exec, "trigger.parameters.SKIP_CHART_RELEASE", "")

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

        startTimeStamp = self._getValue(exec, "startTime", exec["buildTime"])
        endTimeStamp = self._getValue(exec, "endTime", None)
        pr["startTime"] = self._parseTimeStamp(startTimeStamp)
        pr["endTime"] = self._parseTimeStamp(endTimeStamp)
        pr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        stages = []

        for stage in exec["stages"]:
            if "Gerrit" in stage["name"] or "Commit" in stage["name"] or \
                    "Check precondition" in stage["name"] or "Stop pipeline" in stage["name"]:
                pass
            elif "Application_Staging" in stage["name"] or "Platform_Staging" in stage["name"]:
                ar = self._toApplicationRecord(stage)
            else:
                stages.append(self._toProductRecord(stage))

        if "release" not in pr["name"]:
            path = self._getValue(exec, "trigger.buildInfo", None)
            if path is not None:
                mr = self._toMicroserviceRecord(exec["trigger"])
            else:
                mr = self._toMicroserviceRecord(exec["trigger"]["parentExecution"]["trigger"])

        records = []
        for sr in stages:
            record = record_util.newEndToEndRecord()
            record["pipeline"] = pr
            record["stage"] = sr

            if "IDUN-PRODUCT-release" in pr["name"]:
                record["application"] = None
                record["microservice"] = None
                durationList = [sr["duration"]]
            elif "release" in pr["name"]:
                record["microservice"] = None
                record["application"] = ar
                durationList = [sr["duration"], ar["duration"]]
            else:
                record["microservice"] = mr
                record["application"] = ar
                durationList = [sr["duration"], ar["duration"], mr["duration"]]
            dr = self._getDurationRecord(durationList)
            record["duration"] = dr
            records.append(record)
        return records

    def _getDurationRecord(self, list):
        dr = record_util.newDurationData()
        total = 0
        for item in list:
            if item is not None:
                total = item + total
        dr["TotalDuration"] = total
        return dr

    def _toProductRecord(self, stage):
        sr = record_util.newProductData()
        sr["id"] = stage["id"]
        sr["childId"] = self._getValue(stage, "context.executionId", None)
        sr["name"] = stage["name"]
        sr["productName"] = self._getProductName(stage["name"])
        sr["type"] = stage["type"]
        sr["status"] = stage["status"]
        sr["chartName"] = self._getValue(stage, "context.pipelineParameters.CHART_NAME", None)
        sr["chartVersion"] = self._getValue(stage, "context.pipelineParameters.CHART_VERSION", None)
        startTimeStamp = self._getValue(stage, "startTime", None)
        endTimeStamp = self._getValue(stage, "endTime", None)
        sr["startTime"] = self._parseTimeStamp(startTimeStamp)
        sr["endTime"] = self._parseTimeStamp(endTimeStamp)
        sr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        return sr

    def _getProductName(self, product):
        return product.split("_")[0]

    def _toApplicationRecord(self, stage):
        ar = record_util.newApplicationData()
        ar["id"] = stage["id"]
        ar["type"] = stage["type"]
        ar["name"] = stage["name"]
        ar["appName"] = self._getAppName(stage["name"])
        ar["status"] = stage["status"]
        ar["chartName"] = self._getValue(stage, "context.pipelineParameters.CHART_NAME", None)
        ar["chartVersion"] = self._getValue(stage, "context.pipelineParameters.CHART_VERSION", None)
        startTimeStamp = self._getValue(stage, "startTime", None)
        endTimeStamp = self._getValue(stage, "endTime", None)
        ar["startTime"] = self._parseTimeStamp(startTimeStamp)
        ar["endTime"] = self._parseTimeStamp(endTimeStamp)
        ar["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        return ar

    def _getAppName(self, name):
        if "Application_Staging" in name:
            appName = name.split("_")[0]
            return appName
        elif "Platform_Staging" in name:
            return "Base Platform"
        else:
            return None

    def _toMicroserviceRecord(self, exec):
        mr = record_util.newMicroserviceData()
        mr["id"] = exec["buildInfo"]["id"]
        mr["status"] = exec["buildInfo"]["result"]
        mr["name"] = exec["properties"]["CHART_NAME"]
        mr["jobName"] = exec["job"]
        mr["buildNumber"] = exec["buildNumber"]
        mr["url"] = exec["buildInfo"]["url"]
        mr["chartName"] = exec["properties"]["CHART_NAME"]
        mr["chartVersion"] = exec["properties"]["CHART_VERSION"]
        mr["commitAuthor"] = exec["properties"]["GIT_COMMIT_AUTHOR"]
        mr["commitMessage"] = exec["properties"]["GIT_COMMIT_SUMMARY"]
        mr["duration"] = exec["buildInfo"]["duration"]
        return mr

    def _toSkipChartRelease(self, skipChartRelease):
        skipChartRelease_str = str(skipChartRelease).strip().lower()
        if skipChartRelease_str == "false":
            return "Deliverable Runs"
        elif skipChartRelease_str == "true":
            return "Non-Deliverable Runs"
        else:
            return "SkipChartRelease is Empty"

    def _toExecutionRecords(self, exec):
        try:
            self._logger.debug("Parsing execution: " + exec["id"])
        except KeyError:
            return []
        csvObj = csvData()
        pr = record_util.newPipelineData()

        pr["id"] = exec["id"]
        pr["status"] = exec["status"]
        pr["finished"] = exec["status"] not in ["RUNNING"]
        pr["application"] = exec["application"]
        mschart_name = self._getValue(
            exec, "trigger.parameters.MICROSERVICE_CHART_NAME", "")
        mschart_version = self._getValue(
            exec, "trigger.parameters.MICROSERVICE_CHART_VERSION", "")
        if (mschart_name and mschart_version and
                str(mschart_name).lower() != "null" and str(mschart_version).lower() != "null"):
            pr["msChartName"] = mschart_name
            pr["msChartVersion"] = mschart_version
        ii_helmfileVersion = self._getValue(
            exec, "trigger.parameters.II_HELMFILE_VERSION", "")
        helmfile_testVersion = self._getValue(
            exec, "trigger.parameters.HELMFILE_FOR_TESTING_VERSION", "")
        upgrade_testing = self._getValue(
            exec, "trigger.parameters.NEEDS_UPGRADE_TESTING", "")
        install_testing = self._getValue(
            exec, "trigger.parameters.NEEDS_INSTALL_TESTING", "")
        if (ii_helmfileVersion and helmfile_testVersion and
                upgrade_testing and install_testing and
                str(ii_helmfileVersion).lower() != "null" and
                str(helmfile_testVersion).lower() != "null" and
                str(upgrade_testing).lower() != "null" and
                str(install_testing).lower() != "null"):
            pr["iiHelmfileVersion"] = ii_helmfileVersion
            pr["helmfileTestVersion"] = helmfile_testVersion
            pr["upgradeTesting"] = upgrade_testing
            pr["installTesting"] = install_testing
        applicationArea, appAlias = csvObj.getAppData(pr["application"])
        if applicationArea and appAlias:
            pr["applicationArea"] = applicationArea
            pr["appAlias"] = appAlias
        intChartName = self._getValue(
            exec, "trigger.parameters.INT_CHART_NAME", "")
        if intChartName:
            chartNameList = str(intChartName).replace(" ", "").split(",")
            pr["intChartName"] = chartNameList
        if "intChartName" in pr:
            subApp = csvObj.getSubAppName(pr["intChartName"])
            if subApp and "appAlias" in pr:
                pr["appAlias"] = subApp
                pr["subApplication"] = subApp
        appChartName = (self._getValue(exec, "trigger.parameters.APP_CHART_NAME", "") or
                        self._getValue(exec, "trigger.parentExecution.trigger.parameters.APP_CHART_NAME", ""))
        if appChartName:
            chartNameList = str(appChartName).replace(" ", "").split(",")
            pr["appChartName"] = chartNameList
        pr["name"] = exec["name"]
        pr["url"] = f"{self._serverBaseUrl}/#/applications/{exec['application']}/executions/details/{exec['id']}"
        pr["chartVersion"] = self._getValue(
            exec, "trigger.parameters.CHART_VERSION", "")
        if not pr["chartVersion"]:
            pr["chartVersion"] = self._getValue(exec, "trigger.parameters.INT_CHART_VERSION", "")
            if not pr["chartVersion"]:
                pr["chartVersion"] = ""
        pr["rcrTag"] = self._getValue(
            exec, "trigger.parameters.RCR_TAG", "")
        pr["rsrTag"] = self._getValue(
            exec, "trigger.parameters.RSR_TAG", "")
        if pr["rsrTag"]:
            pr["parentPipelineName"] = exec["name"]
        pr["rcaTag"] = self._getValue(
            exec, "trigger.parameters.RCA_TAG", "")
        pr["eopTag"] = self._getValue(
            exec, "trigger.parameters.EOP_TAG", "")
        pr["eoaTag"] = self._getValue(
            exec, "trigger.parameters.EOA_TAG", "")
        pr["esoaTag"] = self._getValue(
            exec, "trigger.parameters.ESOA_TAG", "")
        pr["rcfTag"] = self._getValue(
            exec, "trigger.parameters.RCF_TAG", "")
        if pr["rcfTag"]:
            pr["parentPipelineName"] = self._getValue(
                exec, "trigger.parentExecution.name", "")
        pr["S2L"] = self._getValue(
            exec, "trigger.parameters.S2L", "")
        pr["R2L"] = self._getValue(
            exec, "trigger.parameters.R2L", "")
        parentSkipChartRelease = self._getValue(exec, "trigger.parameters.SKIP_CHART_RELEASE", None)
        childSkipChartRelease = self._getValue(exec, "trigger.parentExecution.trigger.parameters."
                                                     "SKIP_CHART_RELEASE", None)
        skipChartRelease = parentSkipChartRelease if parentSkipChartRelease is not None else childSkipChartRelease
        if skipChartRelease is None:
            skipChartRelease = ""
        else:
            pr["skipChartRelease"] = skipChartRelease
            pr["chartRelease"] = self._toSkipChartRelease(skipChartRelease)

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

        pr["chartName"] = (self._getValue(
            exec, "trigger.parameters.CHART_NAME", "") or
            self._getValue(exec, "trigger.parameters.APP_NAME", ""))
        if not pr["chartName"]:
            stages = self._getValue(exec, "trigger.parentExecution.stages", [])
            for stage in stages:
                context = self._getValue(stage, "context", {})
                pipelineParameters = self._getValue(context, "pipelineParameters", {})
                name = self._getValue(pipelineParameters, "name", None)
                if name != '${execution.trigger.parameters.CHART_NAME}' and name:
                    pr["chartName"] = name
                    break
                if not pr["chartName"]:
                    context = self._getValue(stage, "context", {})
                    parameters = self._getValue(context, "parameters", {})
                    chartName = self._getValue(parameters, "CHART_NAME", None)
                    if chartName:
                        pr["chartName"] = chartName
                        break
                else:
                    pr["chartName"] = ""
        applicationArea, appAlias = csvObj.getProductData(pr["chartName"])
        if applicationArea and appAlias:
            pr["applicationArea"] = applicationArea
            pr["appAlias"] = appAlias
        if pr["service"] == "IDUN-PRODUCT-release-E2E-Flow":
            pr["chartName"] = "eic_helm_cr"
        if pr["service"] == "deployment-manager-submit-flow-integration-E2E-Flow":
            pr["chartName"] = "deploy-mgr-cr"

        startTimeStamp = self._getValue(exec, "startTime", exec["buildTime"])
        endTimeStamp = self._getValue(exec, "endTime", None)
        pr["startTime"] = self._parseTimeStamp(startTimeStamp)
        pr["endTime"] = self._parseTimeStamp(endTimeStamp)
        pr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        pr["week"] = None
        if endTimeStamp:
            pr["week"] = self._getWeekNumber(endTimeStamp)
        stages = []
        for stage in exec["stages"]:
            stages.append(self._toStageRecord(stage))

        pr["passed"] = len(
            list(filter(lambda x: not x["passed"], stages))) == 0
        team = TeamLib(self._username, self._password)
        if pr["chartName"] in pr["service"]:
            tr = team.getTeamRecord(pr["chartName"], pr["name"])
        else:
            tr = team.getTeamRecord(pr["service"], pr["chartName"])
        records = []
        for sr in stages:
            record = record_util.newExecutionRecord()
            record["pipeline"] = pr
            record["stage"] = sr
            record["team"] = tr
            records.append(record)
        return records

    def _toExecutionUpgradeRecords(self, exec, csvDetails):
        self._logger.debug("Parsing execution: " + exec["id"])
        pr = record_util.newPipelineUpgradeData()
        csvObj = csvData()

        pr["id"] = exec["id"]
        pr["status"] = exec["status"]
        pr["finished"] = exec["status"] not in ["RUNNING"]
        pr["application"] = exec["application"]
        pr["name"] = exec["name"]
        pr["url"] = f"{self._serverBaseUrl}/#/applications/{exec['application']}/executions/details/{exec['id']}"
        pr["chartVersion"] = self._getValue(
            exec, "trigger.parameters.CHART_VERSION", "")
        if not pr["chartVersion"]:
            pr["chartVersion"] = self._getValue(exec, "trigger.parameters.INT_CHART_VERSION", "")
            if not pr["chartVersion"]:
                pr["chartVersion"] = ""
        applicationArea, appAlias = csvObj.getAppData(pr["application"])
        if applicationArea and appAlias:
            pr["applicationArea"] = applicationArea
            pr["appAlias"] = appAlias

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
        ii_helmfileVersion = self._getValue(
            exec, "trigger.parameters.II_HELMFILE_VERSION", "")
        helmfile_testVersion = self._getValue(
            exec, "trigger.parameters.HELMFILE_FOR_TESTING_VERSION", "")
        upgrade_testing = self._getValue(
            exec, "trigger.parameters.NEEDS_UPGRADE_TESTING", "")
        install_testing = self._getValue(
            exec, "trigger.parameters.NEEDS_INSTALL_TESTING", "")
        if (ii_helmfileVersion and helmfile_testVersion and
                upgrade_testing and install_testing and
                str(ii_helmfileVersion).lower() != "null" and
                str(helmfile_testVersion).lower() != "null" and
                str(upgrade_testing).lower() != "null" and
                str(install_testing).lower() != "null"):
            pr["iiHelmfileVersion"] = ii_helmfileVersion
            pr["helmfileTestVersion"] = helmfile_testVersion
            pr["upgradeTesting"] = upgrade_testing
            pr["installTesting"] = install_testing

        pr["chartName"] = (self._getValue(
            exec, "trigger.parameters.CHART_NAME", "") or
            self._getValue(exec, "trigger.parameters.APP_NAME", ""))
        if not pr["chartName"]:
            stages = self._getValue(exec, "trigger.parentExecution.stages", [])
            for stage in stages:
                context = self._getValue(stage, "context", {})
                pipelineParameters = self._getValue(context, "pipelineParameters", {})
                name = self._getValue(pipelineParameters, "name", None)
                if name != '${execution.trigger.parameters.CHART_NAME}' and name:
                    pr["chartName"] = name
                    break
                if not pr["chartName"]:
                    context = self._getValue(stage, "context", {})
                    parameters = self._getValue(context, "parameters", {})
                    chartName = self._getValue(parameters, "CHART_NAME", None)
                    if chartName:
                        pr["chartName"] = chartName
                        break
                else:
                    pr["chartName"] = ""
        if pr["service"] == "IDUN-PRODUCT-release-E2E-Flow":
            pr["chartName"] = "eic_helm_cr"
        if pr["service"] == "deployment-manager-submit-flow-integration-E2E-Flow":
            pr["chartName"] = "deploy-mgr-cr"
        parentSkipChartRelease = self._getValue(exec, "trigger.parameters.SKIP_CHART_RELEASE", None)
        childSkipChartRelease = self._getValue(exec, "trigger.parentExecution.trigger.parameters."
                                                     "SKIP_CHART_RELEASE", None)
        skipChartRelease = parentSkipChartRelease if parentSkipChartRelease is not None else childSkipChartRelease
        if skipChartRelease is None:
            skipChartRelease = ""
        else:
            pr["skipChartRelease"] = skipChartRelease
            pr["chartRelease"] = self._toSkipChartRelease(skipChartRelease)

        startTimeStamp = self._getValue(exec, "startTime", exec["buildTime"])
        endTimeStamp = self._getValue(exec, "endTime", None)
        pr["startTime"] = self._parseTimeStamp(startTimeStamp)
        pr["endTime"] = self._parseTimeStamp(endTimeStamp)
        pr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        stages = []
        for stage in exec["stages"]:
            if ((pr["name"] == "eic-release-upgrade-flow" or pr["name"] == "eic-release-install-flow") and
                    pr["service"] == "eic-release-s2l-upgrade-metrics"):
                if csvDetails.get('tagValue') == "Release_Staging_Child_Flow":
                    if (
                        (stage["name"] == csvDetails.get("upgradeStage") or
                         stage["name"] == csvDetails.get("installStage")) and
                        stage["status"] not in ["RUNNING", "SKIPPED", "NOT_STARTED", "FAILED_CONTINUE"]
                    ):
                        stageRecord = self._toStageRecord(stage)
                        # Get the result dictionary by passing stage job url
                        queryUrl = stageRecord["jobUrl"]
                        response = requests.get(queryUrl + "/api/json", auth=self._auth)
                        self._logger.debug(response.json(), response.text)
                        artifacts = response.json().get("artifacts", [])
                        if pr["name"] == "eic-release-upgrade-flow":
                            pr["totalUpgradeDuration"] = self.getArtifactFileUpgradeData(artifacts, queryUrl,
                                                                                         "DEPLOYMENT_TIME", csvDetails)
                        elif pr["name"] == "eic-release-install-flow":
                            pr["totalInstallDuration"] = self.getArtifactFileUpgradeData(artifacts, queryUrl,
                                                                                         "DEPLOYMENT_TIME", csvDetails)
                        else:
                            self._logger.debug("No Application Upgraded")
                        pr["deploymentName"] = self._getValue(exec, "trigger.parameters.DEPLOYMENT_NAME", "")
                        pr["deploymentManagerVersion"] = self.getArtifactFileUpgradeData(artifacts, queryUrl,
                                                                                         "DEPLOYMENT_MANAGER_VERSION",
                                                                                         csvDetails)
                        pr["parentPipelineId"] = self._getValue(exec, "trigger.parentExecution.id", "")
                        pr["parentPipelineName"] = pr["service"]
                        upgradeRecords = self.getUpgradeInstallAppsData(artifacts, queryUrl, csvDetails)
                        self._logger.debug(f"Release Upgraded documents: {upgradeRecords}")
                        if upgradeRecords is not None:
                            merged_list = [{**stageRecord, **doc} for doc in upgradeRecords]
                            for docs in merged_list:
                                stages.append(docs)

                    if (stage["name"] == csvDetails.get("k6Stage") and stage["status"] not in
                            ["RUNNING", "SKIPPED", "NOT_STARTED"]):
                        stageRecord = self._toStageRecord(stage)
                        # To get the K6 stage Job details
                        records = self.getK6Results(exec, csvDetails)
                        self._logger.debug(f"k6 Upgraded documents: {csvDetails}")
                        merged_list = [{**stageRecord, **doc} for doc in records]
                        for record in merged_list:
                            stages.append(record)
            if csvDetails.get("tagValue") == "Release_Staging":
                if pr["name"] == "Scheduled_eic-baseline-II":
                    if (stage["name"] == csvDetails.get("installStage") and stage["status"]
                            not in ["RUNNING", "SKIPPED", "NOT_STARTED", "FAILED_CONTINUE"]):
                        stageRecord = self._toStageRecord(stage)
                        # Get the result dictionary by passing stage job url
                        queryUrl = stageRecord["jobUrl"]
                        response = requests.get(queryUrl + "/api/json", auth=self._auth)
                        artifacts = response.json().get("artifacts", [])
                        pr["parentPipelineName"] = pr["name"]
                        pr["totalInstallDuration"] = self.getArtifactFileUpgradeData(artifacts, queryUrl,
                                                                                     "DEPLOYMENT_TIME", csvDetails)
                        pr["deploymentName"] = self._getValue(exec, "trigger.parameters.ENV_NAME", "")
                        pr["deploymentManagerVersion"] = self.getArtifactFileUpgradeData(artifacts, queryUrl,
                                                                                         "DEPLOYMENT_MANAGER_VERSION",
                                                                                         csvDetails)
                        installRecords = self.getUpgradeInstallAppsData(artifacts, queryUrl, csvDetails)
                        self._logger.debug(f"Release Installed documents: {installRecords}")
                        if installRecords is not None:
                            merged_list = [{**stageRecord, **doc} for doc in installRecords]
                            for docs in merged_list:
                                stages.append(docs)

            if csvDetails.get("tagValue") == "Product_Staging":
                if (pr["name"] == "product-staging" and stage["name"] == csvDetails.get("upgradeStage") and
                        stage["status"] not in ["RUNNING", "SKIPPED", "NOT_STARTED", "FAILED_CONTINUE"]):
                    stageRecord = self._toStageRecord(stage)
                    # Get the result dictionary by passing stage job url
                    queryUrl = stageRecord["jobUrl"]
                    response = requests.get(queryUrl + "/api/json", auth=self._auth)
                    self._logger.debug(response.json(), response.text)
                    artifacts = response.json().get("artifacts", [])
                    upgradeRecords = self.getUpgradeInstallAppsData(artifacts, queryUrl, csvDetails)
                    self._logger.debug(f"Product Staging Upgraded Records: {upgradeRecords}")
                    merged_list = [{**stageRecord, **doc} for doc in upgradeRecords]
                    for docs in merged_list:
                        stages.append(docs)

            if ((pr["name"] == "Deployment_verification" and csvDetails.get('tagValue') == "App_Staging_Child_Flow") or
                    (pr["application"].startswith("base-platform-") and csvDetails.get('tagValue') == "App_Staging")):
                stageRecord = self._toStageRecord(stage)
                # Get the deployment name for app child flows
                if (stage["name"] == "Reserve Namespace" and stage["status"]
                        not in ["RUNNING", "SKIPPED", "NOT_STARTED", "FAILED_CONTINUE"]):
                    pr["deploymentName"] = stageRecord["deploymentName"]
                if (stage["name"] == csvDetails.get("upgradeStage") and stage["status"]
                        not in ["RUNNING", "SKIPPED", "NOT_STARTED", "FAILED_CONTINUE"]):
                    # Get the result dictionary by passing stage job url
                    queryUrl = stageRecord["jobUrl"]
                    response = requests.get(queryUrl + "/api/json", auth=self._auth)
                    artifacts = response.json().get("artifacts", [])
                    pr["parentPipelineName"] = pr["service"]
                    pr["totalUpgradeDuration"] = self.getArtifactFileUpgradeData(
                        artifacts, queryUrl, "DEPLOYMENT_TIME", csvDetails)
                    pr["deploymentManagerVersion"] = self.getArtifactFileUpgradeData(
                        artifacts, queryUrl, "DEPLOYMENT_MANAGER_VERSION", csvDetails)
                    pr["parentPipelineId"] = self._getValue(exec, "trigger.parentExecution.id", "")
                    upgradeRecords = self.getUpgradeInstallAppsData(artifacts, queryUrl, csvDetails)
                    self._logger.debug(f"Application Staging Upgraded Records: {upgradeRecords}")
                    if upgradeRecords is not None:
                        merged_list = [{**stageRecord, **doc} for doc in upgradeRecords]
                        for docs in merged_list:
                            stages.append(docs)

            if csvDetails.get("tagValue") == "PE_Delivery_Staging":
                if (stage["name"] == csvDetails.get("stabilityTestContinuosStage") or stage["name"]
                        == csvDetails.get("stabilityADCTestContinuosStage") and stage["status"] not in
                        ["SKIPPED", "NOT_STARTED", "FAILED_CONTINUE", "TERMINAL"]):
                    stageRecord = self._toStageRecord(stage)
                    queryUrl = stageRecord["jobUrl"]
                    response = requests.get(queryUrl + "consoleText/", auth=self._auth)
                    records = self.getStabilityStageData(response.text)
                    merged_list = [{**stageRecord, **doc} for doc in records]
                    for docs in merged_list:
                        stages.append(docs)

        pr["passed"] = len(
            list(filter(lambda x: not x["passed"], stages))) == 0
        records = []
        for sr in stages:
            record = record_util.newExecutionUpgradeRecord()
            record["pipeline"] = pr
            record["stage"] = sr
            records.append(record)
        return records

    def _isPassed(self, status):
        return status in ["SUCCEEDED", "SKIPPED", "NOT_STARTED", "RUNNING", "SUCCESS", "PAUSED"]

    def _isFinished(self, status):
        return status not in ["RUNNING", "PAUSED"]

    def _toStageRecord(self, stage):
        sr = record_util.newStageData()
        sr["id"] = stage["id"]
        sr["name"] = stage["name"]
        sr["type"] = stage["type"]
        sr["finished"] = self._isFinished(stage["status"])
        sr["pipeline"] = stage["context"]["pipeline"] if stage["type"] == "pipeline" else None

        sr["status"] = stage["status"]
        if sr["type"] == "pipeline":
            sr["jobUrl"] = self._getValue(stage, "outputs.buildInfo.url", None)
        else:
            sr["jobUrl"] = self._getValue(stage, "context.buildInfo.url", None)
        sr["chartVersion"] = self._getValue(stage, "context.INT_CHART_VERSION", None)
        sr["jobFullDisplayName"] = self._getValue(
            stage, "context.buildInfo.fullDisplayName", None)
        sr["passed"] = self._isPassed(sr["status"])
        sr["deploymentName"] = (self._getValue(stage, "outputs.RESOURCE_NAME", None) or
                                self._getValue(stage, "context.pipelineParameters.DEPLOYMENT_NAME", None)
                                or self._getValue(stage, "context.pipelineParameters.RESOURCE_NAME", None)
                                or self._getValue(stage, "context.RESOURCE_NAME", None))
        if sr["deploymentName"] is not None:
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

        startTimeStamp = self._getValue(stage, "startTime", None)
        endTimeStamp = self._getValue(stage, "endTime", None)
        sr["startTime"] = self._parseTimeStamp(startTimeStamp)
        sr["endTime"] = self._parseTimeStamp(endTimeStamp)
        sr["duration"] = self._getDuration(startTimeStamp, endTimeStamp)
        return sr

    def getUpgradeInstallAppsData(self, artifacts, queryUrl, csvData):
        for artifact in artifacts:
            if ((csvData.get('tagValue') == "Release_Staging_Child_Flow" or csvData.get('tagValue') ==
                 "Release_Staging") and csvData.get("upgradeYamlFile") in artifact["fileName"]):
                appsYamlData = self.getYamldata(queryUrl, artifact['relativePath'])
                # get the application names which are upgraded
                upgradeInstallAppsData = self._toUpgradeInstallStageRecords(appsYamlData)
                upgradeInstallRecords = []
                # get the yaml content of deploy-timing.yaml
                for rec in upgradeInstallAppsData:
                    upgradeInstall = self._toUpgradeInstallRecords(rec)
                    # Filter data only for Upgrades
                    if upgradeInstall is not None:
                        upgradeInstallRecords.append(upgradeInstall)
                return upgradeInstallRecords

            if (csvData.get('tagValue') == "Product_Staging" and
                    str(csvData.get("upgradeLogFile")) in artifact["fileName"]):
                # get the yaml content of upgrade.log file
                appsYamlData = self.getYamldata(queryUrl, artifact['relativePath'])
                # get the yaml content of deploy-timing.yaml
                upgradeInstallAppsYamlData = self.getYamldata(queryUrl, csvData.get("upgradeYamlFile"))
                # get the application names only which are upgraded
                apps = self._toUpgradeAppsRecords(appsYamlData)
                # get the yaml content of application which are upgraded
                upgradeAppsData = self._toUpgradeInstallStageRecords(upgradeInstallAppsYamlData)
                upgradeInstallRecords = []
                for rec in upgradeAppsData:
                    for app in apps:
                        if app == rec["Release"]:
                            upgrade = self._toUpgradeInstallRecords(rec)
                            # Filter data only for Upgrades
                            if upgrade is not None:
                                upgradeInstallRecords.append(upgrade)
                return upgradeInstallRecords

            if ((csvData.get('tagValue') == "App_Staging_Child_Flow" or csvData.get('tagValue') == "App_Staging") and
                    str(csvData.get("upgradeLogFile")) in artifact["fileName"]):
                # get the yaml content of upgrade.log file
                appsYamlData = self.getYamldata(queryUrl, artifact['relativePath'])
                # get the yaml content of deploy-timing.yaml
                upgrdadeAppsYamlData = self.getYamldata(queryUrl, csvData.get("upgradeYamlFile"))
                # get the application names only which are upgraded
                apps = self._toUpgradeAppsRecords(appsYamlData)
                # get the yaml content of application which are upgraded
                upgradeAppsData = self._toUpgradeInstallStageRecords(upgrdadeAppsYamlData)
                logging.info(f"Application Upgraded data: {upgradeAppsData}")
                upgradeInstallRecords = []
                for rec in upgradeAppsData:
                    for app in apps:
                        if app == rec["Release"]:
                            upgrade = self._toUpgradeInstallRecords(rec)
                            # Filter data only for Upgrades
                            if upgrade is not None:
                                upgradeInstallRecords.append(upgrade)
                return upgradeInstallRecords

    def getYamldata(self, queryUrl, artifact):
        url = f"{queryUrl}/artifact/{artifact}"
        response = requests.get(url, auth=self._auth)
        self._logger.debug(response.status_code, response, response.text)
        yamlData = response.content
        return yamlData

    def _toUpgradeInstallStageRecords(self, yamlData):
        input_string = str(yamlData.decode('utf-8'))
        sections = input_string.split("\n\n")
        result_dicts = []
        for section in sections:
            section_dict = {}
            lines = section.strip().split('\n')
            for line in lines:
                if ": " in line:
                    key, value = line.strip().split(": ", 1)
                    section_dict[key] = value
                else:
                    # Handle lines without ": " delimiter
                    section_dict[line.strip()] = ""
            result_dicts.append(section_dict)
        result_dicts = [d for d in result_dicts if any(d.values())]
        return result_dicts

    def _toUpgradeAppsRecords(self, log_data):
        upgradedApps = []
        if log_data:
            log_data = log_data.decode('utf-8')
            match = re.search(r'----- Upgraded -----\n(.*?)(?=\n----- Uninstalled -----|$)', log_data, re.DOTALL)
            if match:
                upgraded_content = match.group(1).strip()
                upgraded_lines = upgraded_content.split('\n')  # Split into lines
                for i in upgraded_lines:
                    if "-----" not in i:
                        for word in i.split():
                            if word.startswith('eric'):
                                upgradedApps.append(word)
            else:
                self._logger.debug("No Applications ----- Upgraded -----")
            return upgradedApps

    def _toUpgradeInstallRecords(self, exec):
        if "Upgrade" in exec:
            upgradeFrom = exec['Upgrade'].split('from ')[1].split(' to ')[0]
            upgradeTo = exec['Upgrade'].split('from ')[1].split(' to ')[1]
            durationTime = str(exec['Duration'])
            ur = {}
            ur["appName"] = str(exec['Release'])
            ur["appRevision"] = str(exec['Revision'])
            ur["appUpgradedFrom"] = upgradeFrom
            ur["appUpgradedTo"] = upgradeTo
            if durationTime != "None":
                ur["appDuration"] = TimeCalculator._toMiliSeconds(self, durationTime)
            else:
                ur["appDuration"] = None
            return ur
        elif "Install" in exec:
            installTo = exec['Install'].split('to ')[1]
            durationTime = str(exec['Duration'])
            ur = {}
            ur["appName"] = str(exec['Release'])
            ur["appRevision"] = str(exec['Revision'])
            ur["appInstalledTo"] = installTo
            if durationTime != "None":
                ur["appDuration"] = TimeCalculator._toMiliSeconds(self, durationTime)
            else:
                ur["appDuration"] = None
            return ur
        else:
            return None

    def getK6Results(self, exec, csvData):
        stageDetails = []
        ur = {}
        for stage in exec["stages"]:
            if stage["name"] == csvData.get("k6Stage"):
                response = requests.get(stage["outputs"]["buildInfo"]["url"] + "/api/json", auth=self._auth)
                ur["jobDuration"] = response.json()["duration"]
                artifacts = response.json().get("artifacts", [])
                ur["releaseTestwareVersion"] = self.getArtifactFileUpgradeData(artifacts,
                                                                               stage["outputs"]["buildInfo"]["url"],
                                                                               "releaseTestwareVersion", csvData)
                ur["testwareVersion"] = self.getArtifactFileUpgradeData(artifacts, stage["outputs"]["buildInfo"]["url"],
                                                                        "testwareVersion", csvData)
                testSuitesData = self._getTestSuitesData(stage["outputs"]["buildInfo"]["url"])
                if testSuitesData is not None:
                    merged_list = [{**ur, **doc} for doc in testSuitesData]
                    for docs in merged_list:
                        stageDetails.append(docs)
        return stageDetails

    def getArtifactFileUpgradeData(self, artifacts, queryUrl, dataKey, csvData):
        for artifact in artifacts:
            if csvData.get("artifactFile") in artifact["fileName"]:
                yamlData = self.getYamldata(queryUrl, artifact["fileName"])
                input_string = str(yamlData.decode('utf-8'))
                sections = input_string.splitlines()
                for section in sections:
                    section_dict = {}
                    if "=" in section:
                        key, value = section.strip().split("=", 1)
                        if dataKey in section and dataKey == "DEPLOYMENT_TIME":
                            section_dict[key] = value
                            return TimeCalculator._toMiliSeconds(self, section_dict[key])
                        if dataKey in section and dataKey == "releaseTestwareVersion":
                            section_dict[key] = value
                            return section_dict[key]
                        if dataKey in section and dataKey == "testwareVersion":
                            section_dict[key] = value
                            return section_dict[key]
                        if dataKey in section and dataKey == "DEPLOYMENT_MANAGER_VERSION":
                            section_dict[key] = value
                            return section_dict[key]

    def getStabilityStageData(self, data):
        lines = data.strip().split('\n')
        jenkinsUrl = "https://fem7s11-eiffel216.eiffel.gic.ericsson.se:8443/jenkins/job"
        resultLines = []
        # Iterate through each line
        for line in lines:
            # Check if the line ends with either "SUCCESS" or "FAILURE"
            if line.strip().endswith(("SUCCESS", "FAILURE")):
                # If it does, append the line to the result_lines list
                resultLines.append(line.strip())
        resultDicts = []
        for item in resultLines:
            # filter records where pod is not present
            if "#" in item:
                item = item.replace("#", "")
            # Splitting the string by spaces
            ur = {}
            splitData = item.split()
            if "Build" in splitData:
                # Extracting the required values
                for i in splitData:
                    if 'eic' in i:
                        ur["keyUrl"] = i
                    if i.isnumeric():
                        ur["jobNumber"] = i
                    if 'SUCCESS' in i or 'FAILURE' in i:
                        ur["jobStatus"] = i
                    if '_VPOD' in i:
                        ur["deployment"] = i
                if 'deployment' not in ur:
                    ur["deployment"] = ""
                ur["jenJobUrl"] = f'{jenkinsUrl}/{ur["keyUrl"]}/{ur["jobNumber"]}'
                records = self._getTestSuitesData(ur["jenJobUrl"])
                merged_list = [{**ur, **doc} for doc in records]
                for rec in merged_list:
                    resultDicts.append(rec)
        return resultDicts

    def _getTestSuitesData(self, url):
        response = requests.get(url + "/api/json", auth=self._auth)
        self._logger.debug(response.json(), response.text)
        path = self._getValue(response.json(), "actions", None)
        resultDicts = []
        for i in path:
            if "text" in i:
                applications_statuses = re.findall(
                    r'<span style="color:blue"><b>(.*?)</b></span>.*?Status: <span style="color:(.*?)">(.*?)</span>',
                    i['text'])
                # self._logger.debug application names and statuses
                for app_name, status_color, status_text in applications_statuses:
                    status = "SUCCESSFUL" if status_text == "SUCCESSFUL" else "FAILURE"
                    resultDicts.append({'testName': app_name, 'testStatus': status})
        return resultDicts

    def _parseTimeStamp(self, timeStamp):
        return None if timeStamp is None else datetime.datetime.fromtimestamp(timeStamp / 1000)

    def _getWeekNumber(self, endTimeStamp):
        return None if (endTimeStamp is None) else datetime.datetime.fromtimestamp(endTimeStamp / 1000).isocalendar()[1]

    def _getDuration(self, timeStampStart, timeStampEnd):
        return None if (timeStampStart is None or timeStampEnd is None) else int(timeStampEnd - timeStampStart)

    def _getValue(self, data, path: str, default=Exception()):
        p = path.split(".")
        value = data
        for node in p:
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

    def getParameterValuesById(self, id):
        queryUrl = self._serverBaseUrl + "/pipelines/" + id
        response = requests.get(queryUrl, auth=self._auth)
        self._logger.info(f"Executing for Pipeline ID: {id}")
        return self.getParameterisedValue(response.json())

    def getParameterisedValue(self, exec):
        csvObj = csvData()
        tagName = csvObj.getTagName(exec, "upgrade_install")
        tagValue = self._getValue(exec, f"trigger.parameters.{tagName}", "")
        if tagValue in ["Release_Staging_Child_Flow", "Product_Staging", "PE_Delivery_Staging",
                        "Release_Staging", "App_Staging_Child_Flow", "App_Staging"]:
            record = (
                csvObj.getUpgradeData(tagValue))
            return exec, record

    def getParentID(self, childID):
        queryUrl = self._serverBaseUrl + "/pipelines/" + childID
        response = requests.get(queryUrl, auth=self._auth)
        self._logger.debug(response, response.text)
        return response.json()["trigger"]["parentExecution"]["id"]

    def getPipelineRecord(self, parentID):
        queryUrl = self._serverBaseUrl + "/pipelines/" + parentID
        response = requests.get(queryUrl, auth=self._auth)
        self._logger.debug(response, response.text)
        return self._toPipelineRecords(response.json())

    def releasePipelineCheck(self, parentID):
        queryUrl = self._serverBaseUrl + "/pipelines/" + parentID
        response = requests.get(queryUrl, auth=self._auth)
        if "release" in response.json()["trigger"]["parentExecution"]["name"]:
            pipelineName = response.json()["trigger"]["parentExecution"]["name"]
            self._logger.debug(f"Release Pipeline:  {pipelineName} found hence omitting the Pipeline registration")
            return True
        return None

    def appStagingCheck(self, parentID):
        queryUrl = self._serverBaseUrl + "/pipelines/" + parentID
        response = requests.get(queryUrl, auth=self._auth)
        if self._getValue(response.json(), "trigger.buildInfo", None) is None and \
                self._getValue(response.json(), "trigger.parentExecution", None) is None:
            self._logger.debug("Application Stage is missing, hence omitting the Pipeline registration")
            return True
        return None

    def adpPipelineCheck(self, parentID):
        queryUrl = self._serverBaseUrl + "/pipelines/" + parentID
        response = requests.get(queryUrl, auth=self._auth)
        path = self._getValue(response.json(), "trigger.parentExecution.stages", None)
        if path is not None:
            for stage in path:
                if "AdpStaging" in stage["name"]:
                    self._logger.debug("ADP found")
                    stageName = stage["name"]
                    self._logger.debug(f"Found ADP Stage: {stageName} hence omitting the Pipeline registration")
                    return True
        return None

    def pipelineStatusCheck(self, parentID):
        queryUrl = self._serverBaseUrl + "/pipelines/" + parentID
        response = requests.get(queryUrl, auth=self._auth)
        if response.json()["status"] == "RUNNING":
            return True
        return None
