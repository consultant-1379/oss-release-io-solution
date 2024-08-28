'''Data structures for index mapping'''


class MapRecords:

    def bfaFailureDataMapping(self):
        return {
            "pipeline": {
                "id": "text",
                "pipelineName": "text",
                "buildNumber": "long",
                "displayName": "text",
                "fem": "text",
                "jobType": "text",
                "url": "text",
                "teamName": "text",
                "slaveHostName": "text",
                "triggerCauses": "text",
                "startingTime": "date",
                "duration": "long",
                "timeZoneOffset": "text",
                "result": "text"},
            "stage": {
                "name": "text",
                "status": "text",
                "startTime": "date",
                "duration": "long"
                }
        }
