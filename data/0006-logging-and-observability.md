# File: 0006-logging-and-observability.md

# ADR-0006: Centralized Logging and Observability

Status: Accepted  
Date: 2023-08-10  

## Context
Logs and metrics are currently scattered. To debug distributed systems, we need centralized observability. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Adopt the ELK stack (Elasticsearch, Logstash, Kibana) for centralized logging. Use Prometheus & Grafana for metrics. Follow CNCF guidelines for observability.

## Consequences
- Unified view of system health.  
- Additional operational overhead (managing Elastic).  
- Potentially high storage costs for logs.  

## Alternatives
- Loki for logs (rejected: less mature in our org at this stage).  
- Cloud provider logging only (rejected: less flexible).  

## References
- [CNCF Observability Whitepaper](https://tag-observability.cncf.io/)  
- Related: [ADR-0002: Database per Service](0002-database-per-service.md)  