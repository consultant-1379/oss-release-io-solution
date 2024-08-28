"""Reading and Fetching data from json files"""
import json


class jsonData:

    def getParametersFromJson(self, JsonPath, dataPath, keyParameter):
        Parameters = {}
        with open(f"/usr/src/app/elk/src/etc/json_files/{JsonPath}", "r") as file:
            data = json.load(file)
        with open(f"/usr/src/app/elk/src/etc/json_files/{dataPath}", "r") as file:
            parametersPath = json.load(file)
        if keyParameter in data:
            for k in data[keyParameter]:
                if k in parametersPath[keyParameter]:
                    Parameters[k] = parametersPath[keyParameter][k]
        return Parameters

    def getJsonParameters(self, parameters):
        stageParameters = {}
        pipelineParameters = {}
        with open("/usr/src/app/elk/src/etc/json_files/parameter.json", "r") as file:
            data = json.load(file)
        for param in parameters:
            for item in data["pipelineParameterConfig"]:
                if param in item:
                    pipelineParameters[param] = item[param]
            for item in data["stageParameterConfig"]:
                if param in item:
                    stageParameters[param] = item[param]
        return pipelineParameters, stageParameters

    def getJsonMapping(self, mapType):
        with open("/usr/src/app/elk/src/etc/mapping_format.json", "r") as file:
            data = json.load(file)
        if mapType in data:
            return data[mapType]
        else:
            return []
