'''def add for new execution record'''


def newExecutionRecord():
    return {
        "pipeline": None,
        "stage": None,
        "jira": None,
        "team": None
    }


def newEndToEndRecord():
    return {
        "pipeline": None,
        "stage": None,
        "application": None,
        "microservice": None,
        "jira": None,
        "duration": None
    }


def newBfaMicroserviceRecord():
    return {
        "pipeline": None,
        "stage": None
    }


def newExecutionUpgradeRecord():
    return {
        "pipeline": None,
        "stage": None
    }


def newPipelineData():
    return {
        "id": "",
        "status": "",
        "finished": False,
        "application": "",
        "name": "",
        "buildNumber": -1,
        "url": "",
        "retrigger": False,
        "chartName": "",
        "service": "",
        "rcrTag": "",
        "rsrTag": "",
        "rcaTag": "",
        "eopTag": "",
        "eoaTag": "",
        "esoaTag": "",
        "rcfTag": "",
        "skipChartRelease": "",
        "chartRelease": "",
        "R2L": False,
        "S2L": False,
        "chartVersion": "",
        "startTime": None,
        "endTime": None,
        "week": None,
        "duration": None,
        "passed": False
    }


def newE2EDoraPipelineData():
    return {
        "id": "",
        "status": "",
        "finished": False,
        "application": "",
        "name": "",
        "buildNumber": -1,
        "url": "",
        "retrigger": False,
        "chartName": "",
        "chartVersion": "",
        "startTime": None,
        "endTime": None,
        "duration": None,
        "passed": False
    }


def newPipelineUpgradeData():
    return {
        "id": "",
        "status": "",
        "finished": False,
        "application": "",
        "name": "",
        "buildNumber": -1,
        "url": "",
        "retrigger": False,
        "chartName": "",
        "chartVersion": "",
        "startTime": None,
        "endTime": None,
        "duration": None,
        "passed": False
    }


def newStageData():
    return {
        "id": "",
        "status": "",
        "passed": False,
        "finished": False,
        "type": "",
        "pipeline": None,
        "name": "",
        "jobUrl": None,
        "chartVersion": None,
        "jobFullDisplayName": None,
        "deploymentName": None,
        "startTime": None,
        "endTime": None,
        "duration": None
    }


def newProductData():
    return {
        "id": "",
        "childId": "",
        "name": "",
        "productName": "",
        "type": "",
        "status": "",
        "chartName": "",
        "chartVersion": None,
        "startTime": None,
        "endTime": None,
        "duration": None,
    }


def newApplicationData():
    return {
        "id": "",
        "type": "",
        "name": "",
        "appName": "",
        "status": "",
        "chartName": "",
        "chartVersion": None,
        "startTime": None,
        "endTime": None,
        "duration": None,
    }


def newMicroserviceData():
    return {
        "id": "",
        "status": "",
        "name": "",
        "jobName": "",
        "buildNumber": None,
        "url": None,
        "chartName": "",
        "chartVersion": None,
        "commitAuthor": "",
        "commitMessage": "",
        "duration": None
    }


def newDurationData():
    return {
        "TotalDuration": None
    }


def newEiapJiraData():
    return {
        "id": "",
        "url": "",
        "type": "",
        "status": "",
        "priority": "",
        "resolution": "",
        "component": "",
        "labels": "",
        "assignee": "",
        "reporter": "",
        "sprint": "",
        "daysOpen": None,
        "teamName": "",
        "raTeam": "",
        "reporterTeamName": "",
        "linkedTickets": [],
        "createdDate": None,
        "issueResolvedBaseline": "",
        "lastUpdated": None,
        "closedDate": None,
        "closedDuration": None,
        "area": None,
        "concluded": False
    }


def newEsoaJiraData():
    return {
        "id": "",
        "url": "",
        "type": "",
        "status": "",
        "priority": "",
        "resolution": "",
        "component": "",
        "labels": "",
        "assignee": "",
        "reporter": "",
        "sprint": "",
        "daysOpen": None,
        "teamName": "",
        "linkedTickets": [],
        "createdDate": None,
        "lastUpdated": None,
        "closedDate": None,
        "closedDuration": None,
        "area": None,
        "concluded": False
    }


def newTeamData():
    return {
        "teamName": "",
        "app": "",
        "program": "",
        "microservice": ""
    }


def bfaFailureCausesData():
    return {
        "id": "",
        "pipeline": {
            "id": "",
            "status": "",
            "application": "",
            "name": "",
            "url": "",
            "startTime": "",
            "endTime": "",
            "duration": ""},
        "stage": {
            "status": None,
            "name": "",
            "jobUrl": "",
            "jobName": "",
            "buildNumber": "",
            "startTime": "",
            "endTime": ""},
        "failureCauses": {
            "project_name": "",
            "fem": "",
            "trigger_causes": "",
            "startingTime": "",
            "duration": "",
            "timeZoneOffset": "",
            "result": ""
            }
    }


def bfaMicroserviceData():
    return {
        "id": "",
        "pipelineName": "",
        "buildNumber": "",
        "displayName": "",
        "fem": "",
        "jobType": "",
        "url": "",
        "teamName": "",
        "slaveHostName": "",
        "triggerCauses": "",
        "startingTime": "",
        "duration": "",
        "timeZoneOffset": "",
        "result": ""
    }


def bfaMicroserviceStageData():
    return {
        "name": "",
        "status": "",
        "startTime": "",
        "duration": ""
    }


def msPipelinesData():
    return {
        "pipelineName": "",
        "fem": "",
        "url": "",
        "pipelineType": "",
        "hybrid": False
    }


def mttrData():
    return {
        "pipeline": {
            "id": "",
            "applicationName": "",
            "name": "",
            "chartName": "",
            "chartRelease": "",
            "conclusion": False,
            "serviceName": "",
            "timeToRestore": ""
            }
    }
