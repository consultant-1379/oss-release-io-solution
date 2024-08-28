# Onboarding a new product into ELK

This document outlines the steps for onboarding a new product into ELK.

## Prerequisite

- Create a new product space.
- Identify the pipelines to be onboarded.
- Add appropriate tags to the pipeline.
- Incase of MTTR request Jira Query from the reporting team.

## Access verification

Ensure you have the correct access to push code changes to these repositories:

- oss-release-io-solution repository (ELK Code).
- oss-release-io-solution-resources repository (ndjson files).

## Implementation in Spinnaker pipeline

- Add "Report Center Registration" stage and associated tags into the pipeline (Refer this ticket (https://  jira-oss.seli.wh.rnd.internal.ericsson.com/browse/SM-155950))
- This stage registers data.
- It retrieves essential pipeline details from Spinnaker into corresponding index patterns.
- Tags(Pipeline Parameters) is used for pipeline identification.

## Creating Product Spaces

To create individual spaces for each product follow the below steps:

- Go to the EIC space in Kibana (the default space).
- Search for "space" in the search bar.
- Click "Create Space."
- Provide name, URL, and description.
- Choose an avatar.
- In the features section, select required dashboard components.
- Click "Create Space."

## Implementation in code

Dashboard visualization is achieved using Python scripts from the oss-release-io-solution repository (oris/elk/src/operators - OSS/com.ericsson.oss.cicd/oss-release-io-solution - Gitiles).

## DORA Metrics Flow chart:

These scripts onboard new products into DORA Metrics.

- data_bridge_image.py
- spinnaker_lib.py
- elastic_lib.py
- record_util.py
- time_utils.py
- team_lib.py 

![DORA_Metrics_Flowchart](/oris/ELK_Documentation_and_Diagrams/Diagrams/DORA_Metrics_Flowchart.png)

## MTTR Flow chart:

These scripts onboard new products into MTTR

- jira_data_bridge_image.py
- jira_helper.py
- record_util.py
- time_utils.py

![MTTR_Flowchart](/oris/ELK_Documentation_and_Diagrams/Diagrams/MTTR_Flowchart.png)

## Index patterns
Index mapping refers to defining how the fields in your data should be stored in Elasticsearch. Proper index mapping is important for optimizing search performance and efficiently organizing your data. 

Steps to create index pattern and mapping

- Go to Kibana and navigate to the "Dev Tools" section.
- Use the following request to create an index and define its mapping by specifying the properties of the fields.

``` bash
PUT /your_index
{
  "mappings": {
    "properties": {
      "field1": {
        "type": "text",
        "index": true
      },
      "field2": {
        "type": "integer"
      }
    }
  }
}
```
- Within the Dev Tools console in Kibana,execute the request to create the index.

```
PUT /your_index
```

- Navigate to Management and Select "Index Patterns" in Kibana.
- Create a New Index Pattern
- Define the Index Pattern
- Review and Create

## Implementation of Dashboard

This flowchart outlines the dashboard creation process.

![Dashboard_Creation_Process_Flowchart](/oris/ELK_Documentation_and_Diagrams/Diagrams/Dashboard_Creation_Process_Flowchart.png)

## Code Review Process

This flowchart illustrates the process of code review and deploying code changes to production.

![Code_Review_Process_Flowchart](/oris/ELK_Documentation_and_Diagrams/Diagrams/Code_Review_Process_Flowchart.png)

## Documentation

After each implementation, the developer is responsible for creating or updating the following documents.

- Design document
- Developer Guide
- User Guide




