"""Reading and Fetching data from csv files"""
import json
import pandas as pd


class csvData:

    def getAppData(self, appAlias):
        path = "/usr/src/app/elk/src/etc/csv_files/application_data.csv"
        df = pd.read_csv(path)
        filtered_data = df[df['SpinnakerAppName'] == appAlias]
        data_dict = filtered_data.to_dict('records')
        apps = []
        appAlias = []
        for record in data_dict:
            apps.append(record["AppAreaAlias"])
            appAlias.append(record["AppNameAlias"])
        return list(set(apps)), list(set(appAlias))

    def getSubAppName(self, chartName):
        path = "/usr/src/app/elk/src/etc/csv_files/application_data.csv"
        df = pd.read_csv(path)
        subApp = []
        for eachChart in chartName:
            df['chartName'] = df['chartName'].fillna('')  # fill NaN values with empty string
            filtered_data = df[df['chartName'].str.contains(eachChart)]
            data_dict = filtered_data.to_dict('records')
            for record in data_dict:
                subApp.append(record["subApplications"])
        return list(set(subApp))

    def getTagName(self, exec, key):
        if key == "upgrade_install":
            df = pd.read_csv(f'/usr/src/app/elk/src/etc/csv_files/{key}.csv')
        elif key == "data_source":
            df = pd.read_csv(f'/usr/src/app/elk/src/etc/csv_files/{key}.csv')
        else:
            df = None
        tags = df["TAG"].tolist()
        tagName = ""
        for k in exec["trigger"]["parameters"]:
            if k in tags:
                tagName = k
                break
        return tagName

    def getCsvTagsData(self, tagValue):
        df = pd.read_csv('/usr/src/app/elk/src/etc/csv_files/data_source.csv')
        filtered_data = df[df['TAG_Value'] == tagValue]
        data_dict = filtered_data.to_dict('records')
        record = data_dict[0]
        tagAlias = record["TAG_Alias"]
        index = record["Index"]
        pipelineJsonPath = record["pipelineJson"]
        stageJsonPath = record["stageJson"]
        dataPath = record["dataPath"]
        return tagAlias, index, pipelineJsonPath, stageJsonPath, dataPath

    def getListOfIndices(self):
        df = pd.read_csv('/usr/src/app/elk/src/etc/csv_files/data_source.csv')
        indices = df["Index"].tolist()
        return indices

    def getStkpidata(self):
        df = pd.read_csv('/usr/src/app/elk/src/etc/csv_files/stkpi_data.csv')
        # store each line contents of csv file to dictionary
        data_list = df.to_dict('records')
        return data_list

    def getAppIndexData(self):
        df = pd.read_csv('/usr/src/app/elk/src/etc/csv_files/app_mttr_index_data.csv', na_filter=False)
        index = df["SourceIndex"].tolist()
        data_dict = {}
        for i in index:
            filteredData = df[df['SourceIndex'] == i]
            data_dict.update(filteredData.to_dict('index'))
        return data_dict

    def readJsonData(self):
        path = "/usr/src/app/elk/src/etc/json_files/team.json"
        with open(path, 'r') as f:
            jsonData = json.load(f)
        result = []
        for appName, appData in jsonData.items():
            newAppData = {'id': appName}
            newAppData.update(appData)
            result.append(newAppData)
        return result

    def getUpgradeData(self, tagValue):
        df = pd.read_csv('/usr/src/app/elk/src/etc/csv_files/upgrade_install.csv')
        filtered_data = df[df['tagValue'] == tagValue]
        data_dict = filtered_data.to_dict('records')
        record = data_dict[0]
        return record

    def getProductData(self, appAlias):
        path = "/usr/src/app/elk/src/etc/csv_files/product_data.csv"
        df = pd.read_csv(path)
        filtered_data = df[df['chartName'] == appAlias]
        data_dict = filtered_data.to_dict('records')
        apps = []
        appAlias = []
        for record in data_dict:
            apps.append(record["AppAreaAlias"])
            appAlias.append(record["AppNameAlias"])
        return list(set(apps)), list(set(appAlias))

    def getProdIndexData(self):
        df = pd.read_csv('/usr/src/app/elk/src/etc/csv_files/prod_mttr_index_data.csv', na_filter=False)
        index = df["SourceIndex"].tolist()
        data_dict = {}
        for i in index:
            filteredData = df[df['SourceIndex'] == i]
            data_dict.update(filteredData.to_dict('index'))
        return data_dict
