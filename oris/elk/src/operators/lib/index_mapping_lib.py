"""index mapping file"""
import logging
from elk.src.operators.lib.json_lib import jsonData

logger = logging.getLogger(__name__)


class Mapping:

    def getDataStructure(self, mapType):
        jsonObj = jsonData()
        mapFun = jsonObj.getJsonMapping(mapType)
        if mapFun:
            mapFormat = {'mappings': {'properties': self.mappingFormat(mapFun)}}
            return mapFormat
        else:
            return []

    def mappingFormat(self, dic):
        mapFormat = {}
        for key, value in dic.items():
            if isinstance(value, dict):
                mapFormat[key] = {'properties': self.mappingFormat(value)}
            else:
                mapFormat[key] = {'type': value}
                if value == 'text':
                    mapFormat[key]['fields'] = {'keyword': {'type': 'keyword', 'ignore_above': 256}}
        return mapFormat
