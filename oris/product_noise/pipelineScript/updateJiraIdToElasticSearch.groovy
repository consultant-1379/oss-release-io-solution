import groovy.json.JsonOutput

pipeline {
    agent any

    stages {
        stage("Update Jira ID to ElasticSearch") {
            steps {
                script {
                    def jiraIDsList = params.jiraIDs.split(',')
                    def categoriesList = params.category.split(',')
                    def statusesList = params.status.split(',')

                    // Valid categories list with standard case for consistency
                    def validCategories = ["CI", "Product Bug", "Product TR", "Under Review", "Testware", "Infra", "Blocked","NULL"]

                    // Validate that all lists have the same length
                    if (!(jiraIDsList.size() == categoriesList.size() && categoriesList.size() == statusesList.size())) {
                        error "The number of JIRA IDs, categories, and statuses must match."
                    }

                    // Transform categories to match the valid list format, ensuring case-insensitivity
                    def transformedCategoriesList = categoriesList.collect { inputCategory ->
                        def normalizedCategory = inputCategory.trim().toLowerCase()
                        def index = validCategories.findIndexOf { it.toLowerCase() == normalizedCategory }
                        if (index == -1) {
                            error "Category '${inputCategory.trim()}' is not valid. Valid categories are: ${validCategories.join(', ')}"
                        } else {
                            validCategories[index] // This will fetch the category in the original case from validCategories
                        }
                    }

                    // Constructing JIRA items list
                    def jiraItems = []
                    jiraIDsList.eachWithIndex { id, index ->
                        jiraItems.add([
                            id: id.trim(),
                            category: transformedCategoriesList[index],
                            status: statusesList[index].trim()
                        ])
                    }
                    def documentId = "$stageId"
                    def deploymentName = "$deploymentName"

                    // Construct payload
                    def payload = [
                        doc: [
                            jiraDetails: jiraItems,
                            deploymentName: deploymentName
                        ]
                    ]
                    def payloadJson = JsonOutput.toJson(payload)

                    // HTTPS Elasticsearch
                    def httpsEsHost = "https://elastic.hahn130.rnd.gic.ericsson.se/product-staging-data/_update"
                    def httpsEsAuth = "-u ${params.USERNAME}:${params.PASSWORD}"
  
                    // Send data to Elasticsearch
                    sendDataToElasticsearch(httpsEsHost, httpsEsAuth, documentId, payloadJson)
                }
            }
        }
    }
}

def sendDataToElasticsearch(esHost, esAuth, documentId, payloadJson) {
    def curlOutput = sh (
        script: """
            set -e
            curl --fail --verbose -XPOST '${esHost}/${documentId}' ${esAuth} -H 'Content-Type: application/json' -d '${payloadJson}' -k
        """,
        returnStdout: true,
        returnStatus: true
    )

    if (curlOutput != 0) {
        error "curl command failed with status code ${curlOutput}"
    }
}
