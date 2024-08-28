//Below code is to configure stageId-activeChoiceReactiveParameter
//Referenced parameters:pipelineExecutionID,stageName
import groovy.json.JsonSlurper
def elasticsearchUrl = "https://elastic.hahn130.rnd.gic.ericsson.se/product-staging-data/_search?q=pipeline.id:%22${pipelineExecutionID}%22%20AND%20(pipeline.status:TERMINAL%20OR%20SUCCEEDED%20OR%20CANCELED%20OR%20BLOCKED)%20AND%20(stage.status:FAILED_CONTINUE%20OR%20CANCELED%20OR%20TERMINAL%20OR%20STOPPED)%20AND%20NOT%20(stage.status:NOT_STARTED%20OR%20SUCCEEDED%20OR%20SKIPPED)%20AND%20pipeline.endTime:%5Bnow-1M/d%20TO%20now%5D&size=10000"
def username = "EIAPREG100"
def password = "CztvYwveBHUp8A2UQtBxDxsB"
def command = """
curl -v -k --user $username:$password $elasticsearchUrl
"""
def process = command.execute()
def responseContent = process.text
def jsonSlurper = new JsonSlurper()
def data = jsonSlurper.parseText(responseContent)
def stageData = data.hits.hits.find {
    it._source.stage.name == stageName
}._source.stage

def stageId = stageData.id

return [stageId]