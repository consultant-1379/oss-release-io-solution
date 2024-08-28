''' importing logging, os, sys, argparse, time. module'''
import logging
from typing import Iterable
from . import record_util


class MttrDataLib:
    logger = logging.getLogger(__name__)

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log,
            format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")

    def formatDataForMTTRIndex(self, data):
        result = []
        chartDict = {}
        if isinstance(data, dict):
            pipeline = data['_source']['pipeline']
            stage = data['_source']['stage']
        chartName = pipeline['chartName']
        status = {
            "pipelineStatus": pipeline['status'],
            "endTime": pipeline['endTime'],
            "buildNumber": pipeline['buildNumber'],
            "ID": pipeline['id'],
            "microServiceVersion": pipeline['chartVersion'],
            "url": pipeline['url'],
            "applicationVersion": stage['chartVersion']
        }
        statusKey = 'successData' if pipeline['status'] == 'SUCCEEDED' else 'failureData'
        if chartName not in chartDict:
            mttrData = record_util.mttrData()
            mttrData["pipeline"]["id"] = pipeline['id']
            mttrData["pipeline"]["applicationName"] = pipeline['application']
            mttrData["pipeline"]["name"] = pipeline['name']
            mttrData["pipeline"]["chartName"] = chartName
            mttrData["pipeline"]["serviceName"] = pipeline['service']
            if pipeline["chartRelease"] != "SkipChartRelease is Empty" or "":
                mttrData["pipeline"]["chartRelease"] = pipeline['chartRelease']
            if 'appAlias' in pipeline:
                mttrData["pipeline"]["appAlias"] = pipeline["appAlias"]
            if 'applicationArea' in pipeline:
                mttrData["pipeline"]["applicationArea"] = pipeline["applicationArea"]
            if 'subApplication' in pipeline:
                mttrData["pipeline"]["subApplication"] = pipeline["subApplication"]
            mttrData[statusKey] = status
            chartDict[chartName] = mttrData
        else:
            statusCount = len([k for k in chartDict[chartName].keys() if k.startswith(statusKey)])
            chartDict[chartName][f"{statusKey}({statusCount + 1})"] = status
        for chartName, chartData in chartDict.items():
            if "chartRelease" in chartData["pipeline"] and not chartData["pipeline"]["chartRelease"]:
                del chartData["pipeline"]["chartRelease"]
            result.append(chartData)
        return result

    def combineTerminalAndSucceededData(self, datas):
        if isinstance(datas, Iterable):
            data = list({item['pipeline']['id']: item for item in datas}.values())
        output = []
        statusDict = {}
        for status in data:
            key = (status['pipeline']['chartName'], status['pipeline']['name'])
            if key not in statusDict:
                statusDict[key] = []
            statusDict[key].append(status)
        for key, statuses in statusDict.items():
            terminalFound = False
            succeededFound = False
            for status in statuses:
                if (
                        'successData' in status and
                        status['successData']['pipelineStatus'] == 'SUCCEEDED' and
                        not terminalFound and not succeededFound
                ):
                    output.append(status.copy())
                    succeededFound = True
                elif (
                        'failureData' in status and
                        status['failureData']['pipelineStatus'] == 'TERMINAL' and
                        not terminalFound
                ):
                    statusCopy = status.copy()
                    output.append(statusCopy)
                    terminalFound = True
                    succeededFound = False
                elif (
                        'successData' in status and
                        status['successData']['pipelineStatus'] == 'SUCCEEDED' and
                        terminalFound and
                        status['successData']['endTime'] > output[-1]['failureData']['endTime']
                ):
                    output[-1]['successData'] = status['successData']
                    terminalFound = False
                    succeededFound = True
        return output

    def updatePreviousWithLatest(self, previousData, latestData):
        previousData, latestData = self.noUpdatePreviousWithLatest(previousData, latestData)
        latestDataCopy = [item.copy() for item in latestData]
        if isinstance(previousData, Iterable):
            for previousDoc in previousData:
                item = previousDoc['_source']['pipeline']['chartName']
                for latestDoc in latestDataCopy:
                    if (
                            'successData' in latestDoc and
                            latestDoc['pipeline']['name'] == previousDoc['_source']['pipeline']['name'] and
                            latestDoc['pipeline']['chartName'] == item
                    ):
                        previousDoc['_source'].update({'successData': latestDoc['successData']})
                        if latestDoc in latestData:
                            latestData.remove(latestDoc)
                        break
            for previousDoc in previousData:
                item = previousDoc['_source']['pipeline']['chartName']
                for latestDoc in latestData:
                    if (
                            previousDoc['_source']['pipeline']['name'] == latestDoc['pipeline']['name'] and
                            item == latestDoc['pipeline']['chartName']
                    ):
                        if (
                                'failureData' in previousDoc['_source'] and
                                'failureData' in latestDoc and
                                previousDoc['_source']['failureData']['pipelineStatus'] == 'TERMINAL' and
                                latestDoc['failureData']['pipelineStatus'] == 'TERMINAL' and
                                'successData' not in previousDoc['_source']
                        ):
                            latestData.remove(latestDoc)
                            break
        previous = []
        if isinstance(previousData, Iterable):
            for data in previousData:
                previous.append(data["_source"])
        return previous, latestData

    def noUpdatePreviousWithLatest(self, previousData, latestData):
        updatedLatestData = []
        for latestDoc in latestData:
            matchFound = False
            if isinstance(previousData, Iterable):
                for previousDoc in previousData:
                    item = previousDoc['_source']['pipeline']['chartName']
                    if (
                            latestDoc['pipeline']['name'] == previousDoc['_source']['pipeline']['name'] and
                            latestDoc['pipeline']['chartName'] == item
                    ):
                        matchFound = True
                        break
                if not matchFound and (
                        'failureData' in latestDoc or
                        ('failureData' in latestDoc and
                         'successData' in latestDoc)
                ):
                    updatedLatestData.append(latestDoc)
                elif matchFound:
                    updatedLatestData.append(latestDoc)
        return previousData, updatedLatestData

    def calculateTR(self, dataToTR):
        for data in dataToTR:
            item = data['_source']
            item['pipeline']['endTime'] = item['failureData']['endTime']
            if 'failureData' in item and 'successData' in item:
                terminalStatus = item['failureData']['pipelineStatus']
                succeededStatus = item['successData']['pipelineStatus']
                if terminalStatus == 'TERMINAL' and succeededStatus == 'SUCCEEDED':
                    item['pipeline']['startTime'] = item['failureData']['endTime']
                    item['pipeline']['endTime'] = item['successData']['endTime']
                    item['pipeline']['timeToRestore'] = item['pipeline']['endTime'] - item['pipeline']['startTime']
                    item['pipeline']['conclusion'] = bool(item['pipeline']['timeToRestore'])
        finalMTTR = []
        for mttrData in dataToTR:
            finalMTTR.append(mttrData["_source"])
        return finalMTTR
