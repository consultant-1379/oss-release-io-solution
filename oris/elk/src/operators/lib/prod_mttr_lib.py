''' importing logging, os, sys, argparse, time. module'''
import copy
import datetime
import logging
from typing import Iterable
from . import record_util
from datetime import timedelta


class MttrDataLib:
    logger = logging.getLogger(__name__)

    def setLogLevel(self, debug):
        log = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log,
            format="%(asctime)s %(name)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")

    def formatDataForMTTRIndex(self, dataList):
        finalData = []
        for data in dataList:
            result = []
            chartDict = {}
            pipeline = data['_source']['pipeline']
            chartName = pipeline['chartName']
            status = {
                "ID": pipeline['id'],
                "pipelineStatus": pipeline['status'],
                "endTime": pipeline['endTime'],
                "buildNumber": pipeline['buildNumber'],
                "serviceName": pipeline['service'],
                "url": pipeline['url'],
                "applicationVersion": pipeline['chartVersion'],
                "microServiceVersion": pipeline['msChartVersion'] if 'msChartVersion' in pipeline else None
            }
            statusKey = 'successData' if pipeline['status'] == 'SUCCEEDED' else 'failureData'
            if chartName not in chartDict:
                mttrData = record_util.mttrData()
                mttrData["pipeline"]["id"] = pipeline['id']
                mttrData["pipeline"]["applicationName"] = pipeline['application']
                mttrData["pipeline"]["name"] = pipeline['name']
                mttrData["pipeline"]["chartName"] = chartName
                if 'msChartName' in pipeline:
                    mttrData["pipeline"]["microService"] = pipeline['msChartName']
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
            for res in result:
                for stagingType in ['product', 'application', 'microService']:
                    result = copy.deepcopy(res)
                    result['pipeline']['stagingType'] = stagingType
                    result['pipeline']['id'] = result['pipeline']['id'] + stagingType
                    if stagingType in ['product', 'microService']:
                        if 'chartName' in result['pipeline']:
                            del result['pipeline']['chartName']
                    finalData.append(result)
        return finalData

    def combineTerminalAndSucceededData(self, data):
        output = []
        statusDict = {}
        for status in data:
            stagingType = status['pipeline'].get('stagingType', '')
            if stagingType == 'application':
                key = (status['pipeline'].get('chartName', ''), status['pipeline'].get('name', ''))
            elif stagingType == 'product':
                key = status['pipeline'].get('name', '')
            elif stagingType == 'microService' and status['pipeline'].get('microService', None):
                key = (status['pipeline'].get('microService', ''), status['pipeline'].get('name', ''))
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
                item = previousDoc['_source']['pipeline'].get('chartName')
                msName = previousDoc['_source']['pipeline'].get('microService')
                staging = previousDoc['_source']['pipeline']['stagingType']
                for latestDoc in latestDataCopy:
                    latestStaging = latestDoc['pipeline']['stagingType']
                    if staging == latestStaging and latestStaging in ['product', 'application', 'microService']:
                        if (
                            'successData' in latestDoc and
                            latestDoc['pipeline']['name'] == previousDoc['_source']['pipeline']['name'] and
                            ((staging == 'product') or
                             (staging == 'application' and item == latestDoc['pipeline'].get('chartName')) or
                             (staging == 'microService' and msName == latestDoc['pipeline'].get('microService')))
                        ):
                            previousDoc['_source'].update({'successData': latestDoc['successData']})
                            if latestDoc in latestData:
                                latestData.remove(latestDoc)
                            break

            for previousDoc in previousData:
                item = previousDoc['_source']['pipeline'].get('chartName')
                msName = previousDoc['_source']['pipeline'].get('microService')
                staging = previousDoc['_source']['pipeline']['stagingType']
                for latestDoc in latestData:
                    latestStaging = latestDoc['pipeline']['stagingType']
                    if staging == latestStaging and latestStaging in ['product', 'application', 'microService']:
                        if (
                            previousDoc['_source']['pipeline']['name'] == latestDoc['pipeline']['name'] and
                            ((staging == 'product') or
                             (staging == 'application' and item == latestDoc['pipeline'].get('chartName')) or
                             (staging == 'microService' and msName == latestDoc['pipeline'].get('microService')))
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
                    staging = previousDoc['_source']['pipeline']['stagingType']
                    item = previousDoc['_source']['pipeline'].get('chartName')
                    msName = previousDoc['_source']['pipeline'].get('microService')
                    if (
                        staging == latestDoc['pipeline']['stagingType'] and
                        staging in ['product', 'application', 'microService']
                    ):
                        if (
                            previousDoc['_source']['pipeline']['name'] == latestDoc['pipeline']['name'] and
                            ((staging == 'product') or
                             (staging == 'application' and item == latestDoc['pipeline'].get('chartName')) or
                             (staging == 'microService' and msName == latestDoc['pipeline'].get('microService')))
                        ):
                            matchFound = True
                            break
                if not matchFound and (
                    'failureData' in latestDoc or
                    ('failureData' in latestDoc and 'successData' in latestDoc)
                ):
                    updatedLatestData.append(latestDoc)
                elif matchFound:
                    updatedLatestData.append(latestDoc)

        return previousData, updatedLatestData

    def calculateTR(self, dataToTR):
        finalMTTR = []
        for data in dataToTR:
            item = data['_source']
            if 'failureData' in item and 'successData' in item:
                startTimeMs = item['failureData']['endTime']
                endTimeMs = item['successData']['endTime']
                item['pipeline']['startTime'] = startTimeMs
                item['pipeline']['endTime'] = endTimeMs
                startTime = datetime.datetime.fromtimestamp(startTimeMs / 1000)
                endTime = datetime.datetime.fromtimestamp(endTimeMs / 1000)
                timeToRestore = endTimeMs - startTimeMs
                weekendCount = 0
                currentTime = startTime
                while currentTime < endTime:
                    if currentTime.weekday() == 5:
                        if (
                            startTime.weekday() in [5, 6] and endTime.weekday() in [5, 6] and
                            (endTime - startTime).days < 2
                        ):
                            break
                        weekendCount += 1
                    currentTime += timedelta(days=1)
                timeToRestore -= weekendCount * 48 * 3600 * 1000
                item['pipeline']['timeToRestore'] = timeToRestore
                item['pipeline']['conclusion'] = timeToRestore > 0
            finalMTTR.append(item)
        return finalMTTR
