''' importing logging, os, sys, argparse, time. module'''
import logging
import time
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.csv_lib import csvData
from elk.src.operators.lib.app_mttr_lib import MttrDataLib
from elk.src.operators.lib.time_utils import TimeCalculator


class AppMTTRBridge:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def getMttrDocData(self):
        csvObj = csvData()
        IndexData = csvObj.getAppIndexData()
        es = ElasticSearchLib(self.username, self.password, "")
        yesterDay = TimeCalculator()
        startTime, endTime = yesterDay.yesterDayDate()
        for datas in IndexData.values():
            finalData = []
            index = datas['SourceIndex']
            indices = [index]
            skipChartRelease = str(datas['SkipChartRelease']).lower()
            tag = datas['Tag']
            value = datas['Value']
            logging.info(f"Getting Existing Data from {index}")
            app = es.getPipelineChartNames(indices, startTime, endTime, skipChartRelease, tag, value)
            for pipelineName, chartNames in app.items():
                for chartName in chartNames:
                    if chartName:
                        data = es.getPipelineData(indices, pipelineName, chartName, startTime,
                                                  endTime, skipChartRelease, tag, value)
                        for i in data:
                            final = MttrDataLib.formatDataForMTTRIndex("", i)
                            finalData.append(final[0])
            finalData = MttrDataLib.combineTerminalAndSucceededData("", finalData)
            logging.info(f"Found {len(finalData)} documents in index {index}")
            ind = datas['MTTRIndex']
            indice = [ind]
            updateConclusion = es.getMttrConclusion(indice)
            logging.info(f"Getting Existing Data from {ind}")
            MTTRLib = MttrDataLib()
            if not updateConclusion:
                finalTodayData = [data for data in finalData if 'failureData' in data]
                self.pushData(finalTodayData, datas['MTTRIndex'], datas['ProductName'])
                logging.info(f"Uploaded {len(finalTodayData)} documents to {datas['MTTRIndex']}")
            else:
                updatedConclusion, finalTodayData = MTTRLib.updatePreviousWithLatest(updateConclusion, finalData)
                self.pushData(updatedConclusion, datas['MTTRIndex'], datas['ProductName'])
                self.pushData(finalTodayData, datas['MTTRIndex'], datas['ProductName'])
            time.sleep(1)
            MTTR = es.getMttrConclusion(indice)
            finalMTTR = MttrDataLib.calculateTR("", MTTR)
            self.pushData(finalMTTR, datas['MTTRIndex'], datas['ProductName'])
            logging.info(f"Uploaded {len(finalTodayData)} documents to {datas['MTTRIndex']}")

    def pushData(self, exec, indexName, productName):
        if productName == 'EIC':
            es = ElasticSearchLib(self.username, self.password, indexName)
            es.updateMTTRDocuments(exec)
