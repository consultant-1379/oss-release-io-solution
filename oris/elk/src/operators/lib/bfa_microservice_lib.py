"""import datetime module """
import logging
import pymongo
import requests
import bson
import copy
from .time_utils import TimeCalculator
from datetime import datetime, timedelta
from . import record_util


class MongoDataBase:

    def __init__(self, username, password):
        self.logger = logging.getLogger(__name__)
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log,
            format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")

    def bfaData(self, femUrl):
        # This function gets the data from mongo DB
        fem = str(femUrl).split(":")[0]
        self.logger.info(f"Microservice pipelines from fem: '{fem}'")
        mongodb = ["mongodb://ossmsci:Bn1cr9Nq8E06aIC@pduoss-idun-ci-mongo-1598-p.seli.gic.ericsson.se:27017/"
                   "pduoss-idun-ci"]
        dbnames = ["pduoss-idun-ci"]
        client = pymongo.MongoClient(mongodb[0])
        db = client[dbnames[0]]
        yesterday = self.yesterdayDate()+"T23:55:00.000Z"
        statdb = db["statistics"]
        # startTime = datetime.strptime("2024-05-31T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ")
        startTime = datetime.strptime(yesterday, "%Y-%m-%dT%H:%M:%S.%fZ")
        statQuery = {"master": fem, "startingTime": {"$gt": startTime}}
        stat = statdb.find(statQuery)
        faildb = db["failureCauses"]
        mongoData = []
        for data in stat:
            projectName = data['projectName']
            jName = str(projectName).lower()
            pipelineSuffixes = ["_precodereview", "_publish", "_release"]
            if any(sufix in jName for sufix in pipelineSuffixes):
                mongoData.append(data)
        return mongoData, femUrl, faildb

    def getDataFromJenkins(self, newPipelines, femUrl, faildb):
        records = []
        for data in newPipelines:
            rec = record_util.bfaMicroserviceData()
            projectName = data['projectName']
            jName = str(projectName).lower()
            buildNum = data['buildNumber']
            self.logger.info(f"MS Pipeline Name : {projectName} and Build Number : {buildNum}")
            rec["id"] = projectName+"-"+str(buildNum)
            rec["pipelineName"] = projectName
            rec["buildNumber"] = buildNum
            rec["displayName"] = str(data["displayName"]).replace(" ", "").replace("\n", "").split("/")[-1]
            rec["fem"] = data["master"]
            rec["jobType"] = self.jobType(jName)
            rec["url"] = f"https://{femUrl}/jenkins/job/{projectName}/{buildNum}"
            stageUrl = (f"https://{femUrl}/jenkins/blue/rest/organizations/jenkins/pipelines/"
                        f"{projectName}/runs/{buildNum}/nodes/?limit=10000")
            stage_data = self.getStageDetails(stageUrl)
            if stage_data:
                stage_data[-1]['last_execution'] = True
            stages = []
            for stage in stage_data:
                stages.append(self.toStageRecords(stage))
            teamName = self.getTeamName(projectName)
            rec["teamName"] = teamName
            rec["slaveHostName"] = data["slaveHostName"]
            rec["triggerCauses"] = data["triggerCauses"]
            startingTime = data["startingTime"]
            rec["startingTime"] = self.milliseconds(startingTime)
            rec["duration"] = data["duration"]
            rec["endTime"] = int(rec["startingTime"]) + int(rec["duration"])
            rec["timeZoneOffset"] = data["timeZoneOffset"]
            rec["result"] = data["result"]
            rec["failureIdentification"] = False
            if rec["result"] == "FAILURE":
                failureList = self.getAllFailures(data, rec, faildb)
                records_for_current_iteration = self.failureRecords(failureList, stages, rec, femUrl)
                records.extend(records_for_current_iteration)
            else:
                records_for_current_iteration = []
                for sr in stages:
                    record = record_util.newBfaMicroserviceRecord()
                    record["pipeline"] = rec
                    record["stage"] = sr
                    records_for_current_iteration.append(record)
                records.extend(records_for_current_iteration)
        return records

    def failureRecords(self, failureList, stages, rec, femUrl):
        # This function checks each stage log and append failures to the respective stage
        records_for_current_iteration = []
        if failureList:
            for sr in stages:
                record = record_util.newBfaMicroserviceRecord()
                record["pipeline"] = rec
                record["pipeline"]["failureIdentification"] = True
                record["stage"] = sr
                stageID = record["stage"]["id"]
                stageName = record["stage"]["name"]
                stageFailures, flag, blueOcenUrl = self.checkFailuresInStage(failureList,
                                                                             stageName, stageID, rec, femUrl)
                record["stage"]["blueOcenUrl"] = blueOcenUrl
                if flag is True and stageName in stageFailures:
                    record["pipeline"]["failureCauses"] = stageFailures[stageName]
                else:
                    if "failureCauses" in record["pipeline"]:
                        record["pipeline"].pop("failureCauses")
                record_copy = copy.deepcopy(record)
                records_for_current_iteration.append(record_copy)
        else:
            for sr in stages:
                record = record_util.newBfaMicroserviceRecord()
                record["pipeline"] = rec
                record["stage"] = sr
                if "last_execution" in record["stage"]:
                    if record["stage"]["last_execution"] is True and record["pipeline"]["result"] == "FAILURE":
                        record["pipeline"]["failureCauses"] = {"failureCauseName": ["Non-Classified failures"]}
                record_copy = copy.deepcopy(record)
                records_for_current_iteration.append(record_copy)
        return records_for_current_iteration

    def getAllFailures(self, data, rec, faildb):
        # This function gets all failures which are registered under Identification problems from mongo DB.
        faluresList = []
        if "failureCauses" in data:
            failures = data['failureCauses']
            for i in range(0, len(failures)):
                allFailures = {"failureCauseName": "", "category": "", "pattern": "", "matchingString": ""}
                failureCause = str(data['failureCauses'][i]["failureCause"])
                allFailures["matchingString"] = str(data['failureCauses'][i]["indications"][0]["matchingString"])
                statID = failureCause.split(", ")[1].split("'")[1]
                failQery = {"_id": bson.ObjectId(statID)}
                fail = faildb.find(failQery)
                for fdata in fail:
                    allFailures["failureCauseName"] = fdata["name"]
                    pattern = str(fdata["indications"][0]["pattern"]).split(".*")[1]
                    allFailures["pattern"] = pattern
                    try:
                        category = fdata["categories"][0]
                    except KeyError:
                        if("_OfficialCI" in rec["failureCauseName"]):
                            category = "CI_Infra"
                        elif("_OfficialNonCI" in rec["failureCauseName"]):
                            category = "Non_CI_Infra"
                    allFailures["category"] = category
                    faluresList.append(allFailures)
        else:
            return []
        return faluresList

    def checkFailuresInStage(self, failureList, stageName, stageID, rec, femUrl):
        # This function checks each failure in stage logs based on stage ID.
        blueOcenUrl = (f"https://{femUrl}/jenkins/blue/rest/organizations/jenkins/pipelines/"
                       f"{rec['pipelineName']}/runs/{rec['buildNumber']}/nodes/{stageID}/log/?start=0")
        response = requests.get(blueOcenUrl, auth=(self.username, self.password))
        stageLog = ""
        stageFailures = {stageName: []}
        flag = False
        if response.status_code == 200:
            stageLog = response.text
        else:
            return stageFailures, flag, blueOcenUrl
        if stageLog:
            for eachFailure in failureList:
                if eachFailure["matchingString"] in stageLog:
                    stageFailures[stageName].append(eachFailure)
                    flag = True
                if "ERROR" in eachFailure["matchingString"][:5]:
                    matchingString = eachFailure["matchingString"][10:]
                    if matchingString in stageLog:
                        stageFailures[stageName].append(eachFailure)
                        flag = True
        return stageFailures, flag, blueOcenUrl

    def jobType(self, projectName):
        jobtype = ""
        if("_precodereview" in projectName):
            jobtype = "pcr"
        elif("_publish_hybrid" in projectName):
            jobtype = "publish_hybrid"
        else:
            if("_publish" in projectName):
                jobtype = "publish"
            elif("_release" in projectName):
                jobtype = "release"
        return jobtype

    def milliseconds(self, startingTime):
        time = str(startingTime).split('.')[0]
        d = datetime.strptime(str(time), '%Y-%m-%d %H:%M:%S')
        millisec = d.timestamp()*1000
        time = int(millisec)
        return time

    def yesterdayDate(self):
        yesterday = (datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
        return yesterday

    def getStageDetails(self, url):
        response = requests.get(url, auth=self.auth)
        records = []
        if response.status_code == 200:
            self.logger.info(f"Stage details fetching from URL: {url}")
            try:
                result = response.json()
                for record in result:
                    records.append(record)
            except ValueError:
                self.logger.error("Invalid JSON response")
        else:
            self.logger.error(f"Failed to fetch stage data for {url}. Status code: {response.status_code}")
        return records

    def toStageRecords(self, stage):
        timeObj = TimeCalculator()
        sr = record_util.bfaMicroserviceStageData()
        sr["id"] = stage["id"]
        sr["name"] = stage["displayName"]
        sr["status"] = stage["result"]
        sr["state"] = stage["state"]
        sr["type"] = stage["type"]
        startTime = stage["startTime"]
        if startTime is not None:
            time = timeObj.stageTimeInMilliSeconds(startTime)
            sr["startTime"] = time
        else:
            sr["startTime"] = startTime
        sr["duration"] = stage["durationInMillis"]
        if "last_execution" in stage:
            sr["last_execution"] = True
        return sr

    def getTeamName(self, pipelineName):
        try:
            microserviceName = pipelineName.split("_")[0]
            url = "https://pdu-oss-tools1.seli.wh.rnd.internal.ericsson.com/team-inventory/api/teams"
            response = requests.get(url)
            if response.status_code == 200:
                res = response.json()
                for i, _ in enumerate(res):
                    team_name = 'NULL'
                    ms_name = res[i]['microservice']
                    if ms_name is not None:
                        team_name = res[i]['name']
                        if team_name == "Rigel":
                            team_name = "Regulus"
                        if microserviceName in ms_name.lower():
                            return team_name
                return "NULL"
            else:
                return "NULL"
        except requests.ConnectionError as error:
            raise requests.ConnectionError from error

    def bfaDataChecking(self, fem, jobName, buildNum):
        mongodb = ["mongodb://ossmsci:Bn1cr9Nq8E06aIC@pduoss-idun-ci-mongo-1598-p.seli.gic.ericsson.se:27017/"
                   "pduoss-idun-ci"]
        dbnames = ["pduoss-idun-ci"]
        client = pymongo.MongoClient(mongodb[0])
        db = client[dbnames[0]]
        statdb = db["statistics"]
        statQuery = {"master": fem, "projectName": jobName, "buildNumber": buildNum}
        count = statdb.count_documents(statQuery)
        femName = ""
        job = ""
        build = ""
        if count == 0:
            femName, job, build = fem, jobName, buildNum
        return femName, job, build
