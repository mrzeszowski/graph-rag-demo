# File: 0009-service-ownership-and-dependency-map.md

# ADR-0009: Define Service Ownership and Dependency Map

Status: Accepted  
Date: 2024-01-10  
Related: [ADR-0004: Adopt API Gateway](0004-adopt-api-gateway.md), [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md), [ADR-0005: Switch to Cloud Pub/Sub](0005-switch-to-cloud-pubsub.md)

## Context
As the number of microservices grows, “who owns what” and “what depends on what” becomes hard to answer from scattered docs. This causes slow incident response, risky changes, and unclear accountability. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Maintain an explicit service ownership and dependency map as a first-class artifact.

The map must be updated whenever we:
- create/rename/deprecate a service,
- change a service’s upstream/downstream dependencies,
- add/remove a produced/consumed event,
- change a public API contract.

## Consequences
- Enables impact analysis for schema changes, auth changes, and platform migrations.
- Improves on-call routing and change approvals.
- Requires ongoing maintenance discipline.

## Alternatives
- Rely on tribal knowledge and architecture diagrams (rejected: quickly outdated).
- Infer relationships from code only (rejected: misses ownership/accountability).

## Knowledge Graph Notes (Structured)
The following statements should be kept in a consistent, machine-readable bullet format.

### Entities
Services (examples; replace with actual names used in the system):
- Service: API Gateway (id: `api-gateway`)
- Service: Order Service (id: `order-service`)
- Service: Inventory Service (id: `inventory-service`)
- Service: Customer Service (id: `customer-service`)
- Service: Billing Service (id: `billing-service`)
- Service: Notification Service (id: `notification-service`)

Owners:
- Team: Platform Team (id: `platform`)
- Team: Commerce Team (id: `commerce`)
- Team: Security Team (id: `security`)

Interfaces:
- API: Public HTTP API (id: `public-http`)
- Event topic: `orders.created`
- Event topic: `inventory.reserved`

### Relationships
Ownership:
- Platform Team OWNS API Gateway
- Commerce Team OWNS Order Service
- Commerce Team OWNS Inventory Service
- Commerce Team OWNS Customer Service

Runtime call dependencies:
- API Gateway CALLS Order Service
- API Gateway CALLS Customer Service
- Order Service CALLS Inventory Service
- Order Service CALLS Billing Service

Event production/consumption:
- Order Service PRODUCES `orders.created`
- Billing Service CONSUMES `orders.created`
- Notification Service CONSUMES `orders.created`
- Inventory Service PRODUCES `inventory.reserved`
- Order Service CONSUMES `inventory.reserved`

Governance hooks (ties to other ADRs):
- Public HTTP API (id: `public-http`) ENFORCED_BY API Gateway (see ADR-0004)
- Service-to-service requests AUTHENTICATED_BY OAuth2 (see ADR-0003; ADR-0007)
- Event streams RUN_ON Google Pub/Sub (id: `cloud-pubsub`) (see ADR-0005)

## References
- Related: [ADR-0004: Adopt API Gateway](0004-adopt-api-gateway.md)
- Related: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md)
- Related: [ADR-0005: Switch to Cloud Pub/Sub](0005-switch-to-cloud-pubsub.md)
- Related: [ADR-0008: Introduce Schema Registry](0008-event-schema-registry.md)

## Metadata
- ADR: ADR-0009
- Service IDs: `api-gateway`; `order-service`; `inventory-service`; `customer-service`; `billing-service`; `notification-service`
- Team IDs: `platform`; `commerce`; `security`
- API ID: `public-http`
- Event topic IDs: `orders.created`; `inventory.reserved`
