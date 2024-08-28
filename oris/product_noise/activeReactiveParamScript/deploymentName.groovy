//Below code is to configure deploymentName-activeChoiceReactiveParameter
//Referenced parameters:pipelineExecutionID
import groovy.json.JsonSlurper
def elasticsearchUrl = "https://elastic.hahn130.rnd.gic.ericsson.se/product-staging-data/_search?q=pipeline.id:%22${pipelineExecutionID}%22%20AND%20(pipeline.status:TERMINAL%20OR%20SUCCEEDED%20OR%20CANCELED%20OR%20BLOCKED)%20AND%20pipeline.endTime:%5Bnow-1M/d%20TO%20now%5D&size=10000"
def username = "EIAPREG100"
def password = "CztvYwveBHUp8A2UQtBxDxsB"
def command = """
curl -v -k --user $username:$password $elasticsearchUrl
"""
def process = command.execute()
def responseContent = process.text

// Find "kohn" followed by the next 3 digits in the response
def match = responseContent =~ /kohn(\d{3})/

// If a match is found, extract the matched value
def deploymentName = match ? match[0][0] : null

def depPrefix = deploymentName ? deploymentName.split('_')[0] : null

return [depPrefix]