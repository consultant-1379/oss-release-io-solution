""" importing NDJSON files to kibana instances """
import requests
import os
from os.path import exists
import subprocess
import logging
LOG = logging.getLogger(__name__)


class DashboardAsCode:

    def __init__(self, commit):
        self.auth = (os.environ["OSS_USER"], os.environ["OSS_PASS"])
        self.commit = commit
        logging.basicConfig()
        self.LOG = logging.getLogger(__name__)
        self.LOG.setLevel(logging.DEBUG)
        self.headers = {'kbn-xsrf': 'true'}

    # Getting files from gerrit repo which are pushed by recent commitID and
    # storing into recent_commitFiles.txt
    def Commit_Files(self):
        os.system("cd {}".format(os.getcwd()))
        os.system("git diff-tree --no-commit-id --name-only -r {} > Latest_Commit_Files.txt".format(self.commit))

    # camparing previous and latest commit ID
    def compareCommitID(self):
        path = os.getcwd() + '/Latest_Commit_ID.txt'
        if (exists(path) is False):
            with open(path, 'w') as file:
                file.write('File is created')
        with open(path, 'r') as file:
            previous_commitID = file.readline().strip("\n").strip()
            latest_commitID = self.commit
            # if previous commit == latest commit, it won't import these file one more time
            if (previous_commitID == latest_commitID):
                os.system("cat Latest_Commit_Files.txt")
                LOG.info('ALREADY THIS COMMIT ID FILES ARE IMPORTED INTO KIBANA AND KIBANA-ECK INSTANCES')
            else:
                LOG.info("\nLATEST COMMIT ID ")
                LOG.info(self.commit)
                LOG.info("\nFILES WHICH ARE FETCHED BY LATEST COMMIT ID ")
                os.system("cat Latest_Commit_Files.txt")
                os.system("echo {} > Latest_Commit_ID.txt".format(self.commit))
                self.NdjsonFilesList()

    def NdjsonFilesList(self):
        ndjson_files = []
        imported_files = []
        not_ndjson = []
        current_files = os.getcwd() + '/Latest_Commit_Files.txt'
        with open(current_files, 'r') as test:
            line = test.readline()
            while line != '':
                file = line.replace('\n', '')
                path = os.getcwd()
                # getting only ndjson files from the Last_commit_Files.txt
                if os.path.exists(file) is True:
                    if (file.split('.')[-1] == 'ndjson'):
                        path = path + '/' + file
                        ndjson_files.append(path)
                        imported_files.append(file)
                    else:
                        not_ndjson.append(file)
                line = test.readline()
        self.ImportFilesToKibana(ndjson_files, imported_files, not_ndjson)

    def ImportFilesToKibana(self, ndjson_files, imported_files, not_ndjson):
        url = "https://data-analytics-kibana.ews.gic.ericsson.se"
        EIC = [url + "/api/saved_objects/_import?overwrite=true"]
        EO = [url + "/s/eo/api/saved_objects/_import?overwrite=true"]
        ESOA = [url + "/s/esoa/api/saved_objects/_import?overwrite=true"]
        CICD = [url + "/s/cicd/api/saved_objects/_import?overwrite=true"]
        AUTOAPPS = [url + "/s/auto-apps/api/saved_objects/_import?overwrite=true"]
        status = []
        for each_path in ndjson_files:
            if "/EIC" in each_path:
                for each_url in EIC:
                    url = each_url
                    result = self.updateDocuments(url, each_path)
                    status.append((result))
            elif "/EO" in each_path:
                for each_url in EO:
                    url = each_url
                    result = self.updateDocuments(url, each_path)
                    status.append((result))
            elif "/ESOA" in each_path:
                for each_url in ESOA:
                    url = each_url
                    result = self.updateDocuments(url, each_path)
                    status.append((result))
            elif "/CICD" in each_path:
                for each_url in CICD:
                    url = each_url
                    result = self.updateDocuments(url, each_path)
                    status.append((result))
            elif "/AUTOAPPS" in each_path:
                for each_url in AUTOAPPS:
                    url = each_url
                    result = self.updateDocuments(url, each_path)
                    status.append((result))
            else:
                pass
        if (len(imported_files) > 0):
            if 200 in status:
                LOG.info('BELOW FILES ARE SUCCESSFULLY IMPORTED INTO KIBANA')
                for i in list(set(imported_files)):
                    LOG.info(i)
            else:
                LOG.info('An Error occured, Unable to post data')
        if (len(not_ndjson) > 0):
            LOG.info('INVALID FILES : ')
            for i in not_ndjson:
                LOG.info(i)

    def updateDocuments(self, url, each_path):
        files = {'file': open(each_path, 'rb')}
        try:
            result = requests.post(url=url, auth=self.auth, files=files, verify=False, headers=self.headers)
            LOG.info("%s is imported in %s.", each_path, url)
            return result.status_code
        except Exception:
            LOG.error("connection failed to : %s", url)


if __name__ == '__main__':

    '''
    this subprocess will clone the repo
    '''
    # Getting latest commit id from the repository
    subprocess.call(['sh', 'oris/elk/src/operators/gerritclone.sh'])
    os.chdir("oss-release-io-solution-resources/")
    Com_ID = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').replace('\n', '')
    a = DashboardAsCode(Com_ID)
    a.Commit_Files()
    a.compareCommitID()
