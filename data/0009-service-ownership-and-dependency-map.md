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
- Service: `api-gateway`
- Service: `order-service`
- Service: `inventory-service`
- Service: `customer-service`
- Service: `billing-service`
- Service: `notification-service`

Owners:
- Team: `platform`
- Team: `commerce`
- Team: `security`

Interfaces:
- API: `public-http`
- Event Topic/Stream: `orders.created`
- Event Topic/Stream: `inventory.reserved`

### Relationships
Ownership:
- `platform` OWNS `api-gateway`
- `commerce` OWNS `order-service`
- `commerce` OWNS `inventory-service`
- `commerce` OWNS `customer-service`

Runtime call dependencies:
- `api-gateway` CALLS `order-service`
- `api-gateway` CALLS `customer-service`
- `order-service` CALLS `inventory-service`
- `order-service` CALLS `billing-service`

Event production/consumption:
- `order-service` PRODUCES `orders.created`
- `billing-service` CONSUMES `orders.created`
- `notification-service` CONSUMES `orders.created`
- `inventory-service` PRODUCES `inventory.reserved`
- `order-service` CONSUMES `inventory.reserved`

Governance hooks (ties to other ADRs):
- `public-http` ENFORCED_BY `api-gateway` (see ADR-0004)
- service-to-service requests AUTHENTICATED_BY `oauth2` (see ADR-0003, ADR-0007)
- event streams RUN_ON `cloud-pubsub` (see ADR-0005)

## References
- Related: [ADR-0004: Adopt API Gateway](0004-adopt-api-gateway.md)
- Related: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md)
- Related: [ADR-0005: Switch to Cloud Pub/Sub](0005-switch-to-cloud-pubsub.md)
- Related: [ADR-0008: Introduce Schema Registry](0008-event-schema-registry.md)
