'''Updating duration to RPT Indices'''
import logging
from datetime import datetime
from packaging.version import parse, InvalidVersion


class RPT:

    def __init__(self):
        logging.basicConfig()
        self.LOG = logging.getLogger(__name__)
        self.LOG.setLevel(logging.DEBUG)

    # This function converts time into milliseconds
    def milliseconds(self, time):
        sp = time.split("T")[1].replace("Z", "").replace(".", ":").split(":")
        milliSeconds = ((int(sp[0])*3600000)+(int(sp[1])*60000)+(int(sp[2])*1000)+(int(sp[3])))
        return milliSeconds

    # This function gives count of missed dates
    def days_between(self, d1, d2):
        d1 = datetime.strptime(d1, "%Y-%m-%d")
        d2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((d2 - d1).days)

    def rptMapping(self, index, es_lib, url):
        result = es_lib.rptMappingLimit(index, url)
        if result.status_code == 200:
            self.LOG.info(f"Mapping Response : {result.content}")
            return True
        else:
            return False

    def rptStatus(self, es_lib, url):
        status = ["Reserved", "Available", "Quarantine", "Refreshing", "Standby"]
        records = []
        for i in status:
            statusRec = es_lib.getStatusDoc(i, url)
            for dobj in statusRec:
                old_status = dobj["_source"]["old"]["0"]["status"]
                res_status = dobj["_source"]["res"]["0"]["status"]
                if(old_status != res_status):
                    dobj["_source"]["id"] = dobj["_id"]
                    records.append(dobj["_source"])
        return records

    def rptVersions(self, es_lib, url):
        status = ["Reserved", "Available", "Quarantine", "Refreshing", "Standby"]
        records = []
        for i in status:
            statusRec = es_lib.getStatusDoc(i, url)
            for dobj in statusRec:
                id = dobj["_id"]
                if "regulus" not in id and "envReg" not in id:
                    old_version = dobj["_source"]["old"]["0"]["properties"]['version']
                    res_version = dobj["_source"]["res"]["0"]["properties"]['version']
                    if(old_version != "N/A" and res_version != "N/A"):
                        try:
                            if(parse(old_version) != parse(res_version)):
                                dobj["_source"]["id"] = id
                                records.append(dobj["_source"])
                        except InvalidVersion:
                            continue
        return records

    def addingDuration(self, es_lib, url):
        es_lib.rmvRPTDoc(url)
        status = ["Reserved", "Available", "Quarantine", "Refreshing", "Standby"]
        for i in status:
            statusRec = es_lib.getStatusDoc(i, url)
            # Status name passed inside query function
            # Below for loop fetch all data which matches status name from yesturday index
            for dobj in statusRec:
                oldDate = dobj["_source"]["old"]["0"]['modifiedOn'].split("T")[0]
                newDate = dobj["_source"]["res"]["0"]['modifiedOn'].split("T")[0]
                # Taking count of missed dates and missed dates to get missed index data by using this values
                countOfmissedDates = self.days_between(oldDate, newDate)-1
                # Taking old and res modifiction date into milliseconds using milliseconds method
                old_ms = self.milliseconds(dobj["_source"]["old"]["0"]['modifiedOn'])
                new_ms = self.milliseconds(dobj["_source"]["res"]["0"]['modifiedOn'])
                oldStatus = dobj["_source"]["old"]["0"]['status']
                # If count of missed dates value >=0 , first it will set duration in current document
                if(countOfmissedDates >= 0):
                    duration = new_ms
                    es_lib.rptUpdateDocument(oldStatus, duration, dobj["_id"], url)
                else:
                    duration = new_ms - old_ms
                    es_lib.rptUpdateDocument(oldStatus, duration, dobj["_id"], url)

    def firstDocDuration(self, index, es_lib, url):
        status_list = ["Reserved", "Available", "Quarantine", "Refreshing", "Standby"]
        env_names = es_lib.rptEnvironments(index, url)
        for i in env_names:
            time = 86400000
            id = ""
            record = None
            for j in status_list:
                envStatusData = es_lib.rptDocDuration(index, j, i, url)
                for dobj in envStatusData:
                    if(self.milliseconds(dobj["_source"]["@timestamp"]) < time):
                        time = self.milliseconds(dobj["_source"]["@timestamp"])
                        id = dobj["_id"]
                        record = dobj
            if record is not None:
                old_date = str(record["_source"]["old"]["0"]["modifiedOn"]).split("T")[0]
                res_date = str(record["_source"]["res"]["0"]["modifiedOn"]).split("T")[0]
                rec_id = record["_id"]
                if old_date == res_date:
                    if "-regulus" in rec_id:
                        id = str(record["_id"])
                    else:
                        id = str(record["_id"])+"-regulus"
                    old = record["_source"]["old"]
                    start_time = str(record["_source"]["@timestamp"]).split("T")[0]+"T00:00:00.000Z"
                    end_time = record["_source"]["old"]["0"]["modifiedOn"]
                    name = record["_source"]["old"]["0"]["name"]
                    first_status = record["_source"]["old"]["0"]["status"]
                    first_pools = record["_source"]["old"]["0"]["pools"]
                    duration = self.milliseconds(record["_source"]["old"]["0"]["modifiedOn"])
                    status = record["_source"]["old"]["0"]["status"]
                    if(status == "Reserved"):
                        status_duration = "reserved_duration"
                    elif(status == "Available"):
                        status_duration = "available_duration"
                    elif(status == "Quarantine"):
                        status_duration = "quarantine_duration"
                    elif(status == "Refreshing"):
                        status_duration = "refreshing_duration"
                    else:
                        status_duration = "standby_duration"
                    doc = {
                        "res": old,
                        "old": {"0": {
                            "name": name,
                            "status": first_status,
                            "pools": first_pools,
                            "modifiedOn": start_time}},
                        "@timestamp": end_time,
                        status_duration: duration
                    }
                    self.LOG.info(f"doc : {doc}")
                    es_lib.rptDocumentsCreate(doc, id, url)

    def lastDocDuration(self, index, es_lib, url):
        status_list = ["Reserved", "Available", "Quarantine", "Refreshing", "Standby"]
        env_names = es_lib.rptEnvironments(index, url)
        for i in env_names:
            time = 0
            id = ""
            record = None
            for j in status_list:
                envStatusData = es_lib.rptDocDuration(index, j, i, url)
                for dobj in envStatusData:
                    if(self.milliseconds(dobj["_source"]["@timestamp"]) > time):
                        time = self.milliseconds(dobj["_source"]["@timestamp"])
                        id = dobj["_id"]
                        record = dobj
            if record is not None:
                rec_id = record["_id"]
                if "-regulus" in rec_id:
                    id = str(record["_id"])
                else:
                    id = str(record["_id"])+"-regulus"
                res = record["_source"]["res"]
                last_time = str(record["_source"]["@timestamp"]).split("T")[0]+"T23:59:59.999Z"
                name = record["_source"]["res"]["0"]["name"]
                last_status = record["_source"]["res"]["0"]["status"]
                last_pools = record["_source"]["res"]["0"]["pools"]
                duration = 86400000 - self.milliseconds(record["_source"]["res"]["0"]["modifiedOn"])
                status = record["_source"]["res"]["0"]["status"]
                if(status == "Reserved"):
                    status_duration = "reserved_duration"
                elif(status == "Available"):
                    status_duration = "available_duration"
                elif(status == "Quarantine"):
                    status_duration = "quarantine_duration"
                elif(status == "Refreshing"):
                    status_duration = "refreshing_duration"
                else:
                    status_duration = "standby_duration"
                doc = {
                    "old": res,
                    "res": {"0": {
                        "name": name,
                        "status": last_status,
                        "pools": last_pools,
                        "modifiedOn": last_time}},
                    "@timestamp": last_time,
                    status_duration: duration
                }
                self.LOG.info(f"doc : {doc}")
                es_lib.rptDocumentsCreate(doc, id, url)

    def addingEnvDocuments(self, index, pre_index, es_lib, url):
        envNames = es_lib.rptEnvironments(index, url)
        preIndex_env = es_lib.rptEnvironments(pre_index, url)
        lst1 = [x for x in envNames if x not in preIndex_env]
        lst2 = [x for x in preIndex_env if x not in envNames]
        missed_envNames = lst1+lst2
        status_list = ["Reserved", "Available", "Quarantine", "Refreshing", "Standby"]
        for i in missed_envNames:
            time = 0
            id = ""
            record = None
            for j in status_list:
                envStatusData = es_lib.rptDocDuration(pre_index, j, i, url)
                for dobj in envStatusData:
                    if(self.milliseconds(dobj["_source"]["@timestamp"]) > time):
                        time = self.milliseconds(dobj["_source"]["@timestamp"])
                        id = dobj["_id"]
                        record = dobj
            if record is not None:
                res_time = index.split("-")[2].replace(".", "-")+"T00:00:00.000Z"
                record["_source"]["res"]["0"]["modifiedOn"] = res_time
                rec_id = str(record["_id"])
                if id.__contains__("-envReg"):
                    id = rec_id
                else:
                    id = str(record["_id"])+"-envReg"
                res = record["_source"]["res"]
                last_time = index.split("-")[2].replace(".", "-")+"T23:59:59.999Z"
                name = record["_source"]["res"]["0"]["name"]
                last_status = record["_source"]["res"]["0"]["status"]
                last_pools = record["_source"]["res"]["0"]["pools"]
                duration = 86400000
                status = record["_source"]["res"]["0"]["status"]
                if(status == "Reserved"):
                    status_duration = "reserved_duration"
                elif(status == "Available"):
                    status_duration = "available_duration"
                elif(status == "Quarantine"):
                    status_duration = "quarantine_duration"
                elif(status == "Refreshing"):
                    status_duration = "refreshing_duration"
                else:
                    status_duration = "standby_duration"
                doc = {
                    "old": res,
                    "res": {"0": {
                        "name": name,
                        "status": last_status,
                        "pools": last_pools,
                        "modifiedOn": last_time}},
                    "@timestamp": last_time,
                    status_duration: duration
                }
                self.LOG.info(f"doc :{doc}")
                es_lib.rptDocumentsCreate(doc, id, url)
