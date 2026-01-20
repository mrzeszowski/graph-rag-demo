# File: 0005-switch-to-cloud-pubsub.md

# ADR-0005: Switch to Cloud Pub/Sub

Status: Accepted  
Date: 2023-06-05  
Supersedes: [ADR-0001: Use Kafka for Event Streaming](0001-use-kafka-for-event-streaming.md)

## Context
Running Kafka clusters proved to be a heavy operational burden. Our cloud provider offers a fully managed Pub/Sub service with lower maintenance overhead. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Switch from Apache Kafka to Google Pub/Sub as the event streaming platform.

## Consequences
- Reduced operational complexity.  
- Easier integration with other cloud services.  
- Risk of vendor lock-in.  
- Requires migration effort from existing Kafka topics.  

## Alternatives
- Continue with self-managed Kafka (rejected: ops cost too high).  
- Consider Confluent Cloud Kafka (rejected: higher cost).  

## References
- [Google Pub/Sub Docs](https://cloud.google.com/pubsub/docs)  
- Supersedes: [ADR-0001](0001-use-kafka-for-event-streaming.md)  

## Metadata
- ADR: ADR-0005
- Supersedes: ADR-0001
- Affects components: All services using event streaming
- Uses technology: Google Pub/Sub
- Replaces technology: Apache Kafka