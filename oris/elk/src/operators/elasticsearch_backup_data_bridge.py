''' importing logging, os, shutil, requests, datetime and subprocess module'''
import logging
import os
import shutil
import requests
import subprocess
from datetime import datetime
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)
logger = logging.getLogger()


class BackupSetup:
    def __init__(self, username, password, oss_user, oss_pass):
        self.elkUsername = username
        self.elkPassword = password
        self.ossAuth = (oss_user, oss_pass)
        self.headers = {"Content-Type": "application/json"}
        self.kib_instances = "https://elastic.hahn130.rnd.gic.ericsson.se/"

    def elasticServiceStatus(self):
        try:
            result = requests.get(url=self.kib_instances,
                                  auth=(self.elkUsername, self.elkPassword), headers=self.headers, verify=False)
            if result.status_code == 200:
                logging.info("Elasticsearch service is UP")
            else:
                logging.info("Elasticsearch is not reachable")
        except ConnectionError as e:
            raise ValueError("Maximum attempts are exceeded hence terminating the execution") from e

    def filterLiveIndices(self):
        result = requests.get(f"{self.kib_instances}_cat/indices?h=index",
                              auth=(self.elkUsername, self.elkPassword), headers=self.headers, verify=False)
        open('https_prod_indices.txt', 'wb').write(result.content)
        with open('https_prod_indices.txt', 'rt') as mf:
            for m in mf:
                if m[0] == ".":
                    pass
                else:
                    with open("https_live_indices.txt", "a+") as a:
                        a.write(m)
        self.backupMapData("https_live_indices")

    def backupMapData(self, name):
        subprocess.run(["cat", name+".txt"], check=True)
        subprocess.run(["mkdir", name], check=True)
        with open(name+".txt", 'r') as f:
            start_time = datetime.now()
            str = start_time.strftime("%Y-%b-%d_%H:%M")
            logger.info(f"Backup start time: {str}")
            for i in f:
                i = i[0:-1]
                logger.info(i)
                output_map = f"--output={name}/{i}_mapping.json"
                output_data = f"--output={name}/{i}_data.json"
                input = f"--input=https://{self.elkUsername}:{self.elkPassword}@elastic.hahn130.rnd.gic.ericsson.se/{i}"
                os.system("NODE_TLS_REJECT_UNAUTHORIZED=0 elasticdump {} {} --type=mapping"
                          .format(input, output_map))
                os.system("NODE_TLS_REJECT_UNAUTHORIZED=0 elasticdump {} {} --type=data --limit=10000"
                          .format(input, output_data))
        self.zipElk(name)

    def zipElk(self, name):
        cur_date = datetime.now()
        str = cur_date.strftime("%Y-%b-%d_%H:%M")
        val = name + "_" + str
        shutil.make_archive(val, "zip", name)
        target_file = val + '.zip'
        artifactory_url = 'https://arm.seli.gic.ericsson.se/artifactory/'
        base_file_name = "ELK-Backup/" + os.path.basename(target_file)
        requests.put("{0}/{1}/{2}".format(artifactory_url, "proj-eric-oss-ci-internal-generic-local",
                                          base_file_name), auth=self.ossAuth, verify=False,
                     data=open(target_file, 'rb'))
        logger.info(f"Zip file created: {target_file} and uploaded to Jfrog Artifactory")
