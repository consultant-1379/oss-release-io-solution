''' importing logging'''
import logging
from elk.src.operators.lib.elastic_lib import ElasticSearchLib
from elk.src.operators.lib.index_mapping_lib import Mapping
from elk.src.operators.lib.json_lib import jsonData

logger = logging.getLogger(__name__)


class IndexMapping:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)

    def mapIndex(self, index, timestampField):
        es = ElasticSearchLib(self.username, self.password, index)
        jsonObj = jsonData()
        checkIndexParameter = jsonObj.getJsonMapping(index)
        if checkIndexParameter:
            checkIndexMapping = es.getExistIndexMapping(index)
            if checkIndexMapping:
                parameterCheck = self.checkParameters(checkIndexMapping, timestampField)
                if parameterCheck is True:
                    es.CreateDataView(index, timestampField, f"test_{index}")
            else:
                self.logger.info("Creating new index with mapping...")
                map = Mapping()
                mapData = map.getDataStructure(index)
                if mapData:
                    parameterCheck = self.checkParameters(mapData, timestampField)
                    if parameterCheck is True:
                        es.createIndexMapping(mapData)
                        es.CreateDataView(index, timestampField, f"test_{index}")
        else:
            checkIndexMapping = es.getExistIndexMapping(index)
            if checkIndexMapping:
                parameterCheck = self.checkParameters(checkIndexMapping, timestampField)
                if parameterCheck is True:
                    es.CreateDataView(index, timestampField, f"test_{index}")
            else:
                raise IndexError("Unable to create index and data view due to unavailability of mapping structure.")

    def checkParameters(self, mapping, parameter_string):
        field_names = parameter_string.split(".")
        map = mapping["mappings"]["properties"]
        count = 0
        for parameter in field_names:
            if parameter in map:
                if "properties" in map[parameter]:
                    map = map[parameter]["properties"]
            else:
                count = count + 1
                raise KeyError(f"'{parameter}' key not found in mapping structure")
        if count > 0:
            return False
        else:
            map = mapping["mappings"]["properties"]
            for i in field_names[:-1]:
                map = map[i]["properties"]
            if map[field_names[-1]]["type"] != "date":
                raise TypeError(f"'{field_names[-1]}' parameter type should be date.")
            return True
