"""import datetime module"""
import logging
import pymongo
import bson


class MongoDB:

    logger = logging.getLogger(__name__)

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log,
            format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")

    def mongoData(self, records, itemName):
        item = itemName
        failureData = []
        mongodb = ["mongodb://ossmsci:Bn1cr9Nq8E06aIC@pduoss-idun-ci-mongo-1598-p.seli.gic.ericsson.se:27017/"
                   "pduoss-idun-ci",
                   "mongodb://osseoci:8C6Og2bhmUQ15Ez@pduosseoci-mongo-1748-m2.seli.gic.ericsson.se:27017/pduosseoci"]
        dbnames = ["pduoss-idun-ci", "pduosseoci"]
        for exec in records:
            for i, n in enumerate(mongodb):
                client = pymongo.MongoClient(n)
                db = client[dbnames[i]]
                statdb = db["statistics"]
                statQuery = {"projectName": exec["stage"]["jobName"],
                             "buildNumber": exec["stage"]["buildNumber"],
                             "result": "FAILURE"}
                stat = statdb.find(statQuery)
                faildb = db["failureCauses"]
                for data in stat:
                    projectName = data['projectName']
                    buildNum = data['buildNumber']
                    exec["id"] = projectName+"-"+str(buildNum)
                    exec["failureCauses"]["project_name"] = data['projectName']
                    exec["failureCauses"]["fem"] = data["master"]
                    exec["failureCauses"]["trigger_causes"] = data["triggerCauses"]
                    exec["failureCauses"]["startingTime"] = data["startingTime"]
                    exec["failureCauses"]["duration"] = data["duration"]
                    exec["failureCauses"]["timeZoneOffset"] = data["timeZoneOffset"]
                    exec["failureCauses"]["result"] = data["result"]
                    if "failureCauses" in data:
                        failureCause = str(data['failureCauses'][0]["failureCause"])
                        statID = failureCause.split(", ")[1].split("'")[1]
                        failQery = {"_id": bson.ObjectId(statID)}
                        fail = faildb.find(failQery)
                        for fdata in fail:
                            try:
                                category = fdata["categories"]
                            except KeyError:
                                category = None
                            exec["failureCauses"]["failureCauseName"] = fdata["name"]
                            exec["failureCauses"]["description"] = fdata["description"]
                            exec["failureCauses"]["categories"] = category
                            if item in ["PROD", "eoPROD"]:
                                if(fdata["name"].__contains__('_App_Product_OfficialCI') or
                                   fdata["name"].__contains__('_Product_Staging_OfficialCI')):
                                    print(f"Both statistics and failureCause data :\n {exec}")
                                    failureData.append(exec)
                            elif item in ["APP"]:
                                if(fdata["name"].__contains__('_App_Product_OfficialCI') or
                                   fdata["name"].__contains__('_App_Staging_OfficialCI')):
                                    print(f"Both statistics and failureCause data :\n {exec}")
                                    failureData.append(exec)
                    else:
                        print(f"only statistics data :\n {exec}")
                        failureData.append(exec)
        return failureData
