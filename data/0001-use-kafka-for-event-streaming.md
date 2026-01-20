# File: 0001-use-kafka-for-event-streaming.md

# ADR-0001: Use Kafka for Event Streaming

Status: Accepted  
Date: 2022-09-14  
Superseded by: [ADR-0005: Switch to Cloud Pub/Sub](0005-switch-to-cloud-pubsub.md)

## Context
We need a reliable messaging backbone to decouple microservices. The initial requirement is to support asynchronous event-driven communication between services such as Order Service, Customer Service, and Inventory Service. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Adopt Apache Kafka as the event streaming platform. Deploy it on our Kubernetes cluster using Confluent for Kubernetes.

## Consequences
- High operational overhead (Kafka clusters are complex to run).  
- Strong community support and integration ecosystem.  
- Enables event replay and retention.  
- Requires training for development and operations teams.

## Alternatives
- RabbitMQ (rejected: less scalable for streaming workloads).  
- Azure Service Bus (rejected: cloud lock-in at this stage).  

## References
- [Kafka documentation](https://kafka.apache.org/documentation/)  
- Related: [ADR-0008: Introduce Schema Registry](0008-event-schema-registry.md)  

## Metadata
- ADR: ADR-0001
- Superseded by: ADR-0005
- Affects components: Order Service; Customer Service; Inventory Service
- Uses technology: Apache Kafka
- Related ADRs: ADR-0005; ADR-0008