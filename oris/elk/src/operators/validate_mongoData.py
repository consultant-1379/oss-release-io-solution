''' importing logging, os, sys, argparse, time. module'''
from datetime import datetime, timedelta
from lib.ms_jenkins_data import JenkinsData
import logging
from lib.bfa_microservice_lib import MongoDataBase
from prettytable import PrettyTable


class mongoDataValidation:

    OKBLUE = '\033[94m'
    OKRED = '\033[91m'
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log)

    def TodayDate(self):
        todayDate = (datetime.today()-timedelta(days=0)).strftime('%Y-%m-%d')
        return todayDate

    def getFemList(self):
        path = "oris/elk/src/etc/fem_list.properties"
        fems = []
        with open(path, 'r') as fp:
            fems = fp.readlines()
        return fems

    def getJenkinsData(self):
        fems = self.getFemList()
        todayDate = self.TodayDate()
        for fem in fems:
            fem = fem.replace("\n", "")
            url = "https://"+fem+":8443/jenkins/api/json?tree=jobs[builds[number,url,result,timestamp]]"
            jenkins_instance = JenkinsData()
            pipelineData = jenkins_instance.pipelineData("EIAPREG100", "CztvYwveBHUp8A2UQtBxDxsB", url, todayDate)
            self.checkMongoDBData(fem, pipelineData)

    def checkMongoDBData(self, fem, pipelineData):
        mongo = MongoDataBase("EIAPREG100", "CztvYwveBHUp8A2UQtBxDxsB")
        if len(pipelineData) != 0:
            logging.info(f"\n{mongoDataValidation.OKBLUE}BELOW LIST OF PIPELINES WHICH"
                         f" TRIGGERED TODAY IN FEM : {fem}{mongoDataValidation.ENDC}")
            logging.info(f"{pipelineData}")
            count = 0
            missedData = {}
            for data in pipelineData.values():
                femName, jobName, build = mongo.bfaDataChecking(fem, data[0], data[1])
                if femName != "":
                    count = count + 1
                    missedData[count] = [femName, jobName, build]
            self.missedDataTable(fem, missedData)
        else:
            logging.info(f"NO PIPELINES TRIGGERED AS OF NOW IN FEM : {fem}")

    def missedDataTable(self, fem, missedData):
        my_table = None
        my_table = PrettyTable(["S.NO", "PIPELINE NAME", "BUILD NUMBER", "JOB URL"])
        row_count = 0
        for k, v in missedData.items():
            jobUrl = f"https://{v[0]}:8443/jenkins/job/{v[1]}/{v[2]}"
            my_table.add_row([k, v[1], v[2], jobUrl])
            row_count += 1
        if row_count > 0:
            logging.info(f"\n{mongoDataValidation.OKRED}BELOW TABLE SHOWS PIPELINES DATA WHICH"
                         f" ARE TRIGGERED TODAY AND MISSED IN MONGO DB{mongoDataValidation.ENDC}\n\n")
            logging.info(my_table)
        else:
            logging.info(f"{mongoDataValidation.OKGREEN}PIPELINES DATA IS "
                         f"UPTO DATE IN MONGO DB OF FEM : {fem}{mongoDataValidation.ENDC}\n\n")


bfa = mongoDataValidation()
bfa.setLogLevel('debug')
bfa.getJenkinsData()
