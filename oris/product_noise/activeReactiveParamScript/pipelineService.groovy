//Below code is to configure pipelineService-activeChoiceParameter
import groovy.json.JsonSlurper
def elasticsearchUrl='https://elastic.hahn130.rnd.gic.ericsson.se/product-staging-data/_search?q=(pipeline.status:TERMINAL%20OR%20SUCCEEDED%20OR%20CANCELED20OR%20BLOCKED)%20AND%20(stage.status:FAILED_CONTINUE%20OR%20CANCELED%20OR%20TERMINAL%20OR%20STOPPED)%20AND%20NOT%20(stage.status:NOT_STARTED%20OR%20SUCCEEDED%20OR%20SKIPPED)%20AND%20pipeline.endTime:%5Bnow-1M/d%20TO%20now%5D&size=10000'
def username = "EIAPREG100"
def password = "CztvYwveBHUp8A2UQtBxDxsB"
def command = """
curl -v -k --user $username:$password $elasticsearchUrl
"""
def process = command.execute()
def responseContent = process.text
def jsonSlurper = new JsonSlurper()
def data = jsonSlurper.parseText(responseContent)
def services = data.hits.hits.collect { it._source.pipeline.service }.unique()
def parameters = []
services.each { service ->
    parameters.add(service)
}
return parameters
