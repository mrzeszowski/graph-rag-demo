# File: 0002-database-per-service.md

# ADR-0002: Database per Service

Status: Accepted  
Date: 2022-11-01  

## Context
Shared databases lead to coupling and slow delivery. To enforce bounded contexts, each service should own its persistence layer. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Each microservice will have its own dedicated database schema (logical or physical). PostgreSQL will be the default choice unless another storage engine is justified.

## Consequences
- Clear ownership boundaries.  
- Harder to implement cross-service queries.  
- Increased infrastructure cost (multiple schemas/instances).  

## Alternatives
- Single shared database (rejected: high coupling).  
- Schema-per-bounded-context (rejected: less isolation).  

## References
- [Microservices.io: Database per service](https://microservices.io/patterns/data/database-per-service.html)  
- Related: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md)  

## Metadata
- ADR: ADR-0002
- Affects components: All microservices
- Uses technology: PostgreSQL (default)
- Decision: Database schema per service
- Related ADRs: ADR-0003