# File: 0006-logging-and-observability.md

# ADR-0008: Introduce Schema Registry for Event Contracts

Status: Accepted  
Date: 2023-10-20  

## Context
Events evolve over time. Without strict schema management, consumers break when producers change payloads. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Adopt Confluent Schema Registry with Avro schemas for all events. Enforce compatibility checks at CI/CD pipelines.

## Consequences
- Strong governance for event contracts.  
- Extra step in developer workflow (must register schema).  
- Consumers can evolve more safely.  

## Alternatives
- JSON-only events without validation (rejected: fragile).  
- Protobuf without registry (rejected: no compatibility enforcement).  

## References
- [Confluent Schema Registry Docs](https://docs.confluent.io/platform/current/schema-registry/index.html)  
- Related: [ADR-0001: Use Kafka](0001-use-kafka-for-event-streaming.md), [ADR-0005: Switch to Pub/Sub](0005-switch-to-cloud-pubsub.md)  