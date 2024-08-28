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


class Backup:
    def __init__(self):
        self.serverBaseUrl = "http://es.hahn051.rnd.gic.ericsson.se/"

    def elkServicecheck(self):
        try:
            result = requests.get(f"{self.serverBaseUrl}")
            if result.status_code == 200:
                logging.info("Elasticsearch service is UP")
        except ConnectionError as e:
            raise ValueError("Maximum attempts are exceeded hence terminating the execution") from e

    def filterLiveIndices(self):
        result = requests.get(f"{self.serverBaseUrl}_cat/indices?h=index")
        open('prod_indices.txt', 'wb').write(result.content)
        with open('prod_indices.txt', 'rt') as mf:
            for m in mf:
                if m[0] == ".":
                    pass
                else:
                    with open("live_indices.txt", "a+") as a:
                        a.write(m)

    def backupMapData(self):
        subprocess.run(["cat", "live_indices.txt"], check=True)
        subprocess.run(["mkdir", "indices_backup"], check=True)
        with open('live_indices.txt', 'r') as f:
            start_time = datetime.now()
            str = start_time.strftime("%Y-%b-%d_%H:%M")
            logger.info(f"Backup start time: {str}")
            for i in f:
                i = i[0:-1]
                logger.info(i)
                ed_input = "--input=http://es.hahn051.rnd.gic.ericsson.se/%s" % i
                ed_output_map = "--output=indices_backup/%s_mapping.json" % i
                ed_output_data = "--output=indices_backup/%s_data.json" % i
                subprocess.run(["elasticdump", ed_input, ed_output_map, "--type=mapping"], check=True)
                subprocess.run(["elasticdump", ed_input, ed_output_data, "--type=data", "--limit=10000"], check=True)
        end_time = datetime.now()
        str = end_time.strftime("%Y-%b-%d_%H:%M")
        logger.info(f"Backup end time: {str}")

    def zipElk(self):
        cur_date = datetime.now()
        str = cur_date.strftime("%Y-%b-%d_%H:%M")
        Backup_Name = "indices_backup_"
        val = Backup_Name+str
        shutil.make_archive(val, "zip", "indices_backup")
        target_file = val+'.zip'
        username = os.environ["OSS_USER"]
        password = os.environ["OSS_PASS"]
        artifactory_url = 'https://arm.seli.gic.ericsson.se/artifactory/'
        base_file_name = "ELK-Backup/"+os.path.basename(target_file)
        requests.put("{0}/{1}/{2}".format(artifactory_url, "proj-eric-oss-ci-internal-generic-local",
                     base_file_name), auth=(username, password), verify=False, data=open(target_file, 'rb'))
        logger.info(f"Zip file created: {target_file}")


b = Backup()
b.elkServicecheck()
b.filterLiveIndices()
b.backupMapData()
b.zipElk()
