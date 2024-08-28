''' importing logging, os, sys, argparse, time. module'''
import logging
from datetime import datetime, timedelta
from elk.src.operators.lib.ms_jenkins_data import JenkinsData
from elk.src.operators.lib.bfa_microservice_lib import MongoDataBase
from prettytable import PrettyTable


class mongoDataValidation:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.OKBLUE = '\033[94m'
        self.OKRED = '\033[91m'
        self.OKGREEN = '\033[92m'
        self.ENDC = '\033[0m'

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log)

    def TodayDate(self):
        todayDate = (datetime.today()-timedelta(days=0)).strftime('%Y-%m-%d')
        return todayDate

    def getFemList(self):
        path = "/usr/src/app/elk/src/etc/fem_list.properties"
        fems = []
        with open(path, 'r') as fp:
            fems = fp.readlines()
        return fems

    def getJenkinsData(self):
        self.setLogLevel('debug')
        fems = self.getFemList()
        todayDate = self.TodayDate()
        for fem in fems:
            femUrl = fem.replace("\n", "")
            url = f"https://{femUrl}/jenkins/api/json?tree=jobs[builds[number,url,result,timestamp]]"
            jenkins_instance = JenkinsData()
            pipelineData = jenkins_instance.pipelineData(self.username, self.password, url, todayDate)
            self.checkMongoDBData(fem, pipelineData)

    def checkMongoDBData(self, fem, pipelineData):
        mongo = MongoDataBase(self.username, self.password)
        if len(pipelineData) != 0:
            logging.info(f"\n{self.OKBLUE}BELOW LIST OF PIPELINES WHICH"
                         f" TRIGGERED TODAY IN FEM : {fem}{self.ENDC}")
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
            logging.info(f"\n{self.OKRED}BELOW TABLE SHOWS PIPELINES DATA WHICH"
                         f" ARE TRIGGERED TODAY AND MISSED IN MONGO DB{self.ENDC}\n\n")
            logging.info(my_table)
        else:
            logging.info(f"{self.OKGREEN}PIPELINES DATA IS "
                         f"UPTO DATE IN MONGO DB OF FEM : {fem}{self.ENDC}\n\n")
