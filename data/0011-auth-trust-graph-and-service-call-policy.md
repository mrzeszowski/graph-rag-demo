# File: 0011-auth-trust-graph-and-service-call-policy.md

# ADR-0011: Define Auth Trust Graph and Service Call Policy

Status: Proposed  
Date: 2024-02-01  
Amends: [ADR-0003: Service-to-Service Authentication with OAuth2](0003-service-to-service-authentication.md)  
Related: [ADR-0007: Deprecate mTLS Authentication](0007-deprecate-mtls-auth.md), [ADR-0004: Adopt API Gateway](0004-adopt-api-gateway.md)

## Context
We have a mechanism choice (OAuth2, formerly sometimes mTLS), but it remains difficult to answer:
- which services are allowed to call which other services,
- what identity is used on each hop,
- what claims/scopes are required,
- where external vs internal trust boundaries exist.

These questions matter for incident response, audits, and safe refactors. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Document service-to-service authorization as an explicit trust graph.

For each allowed edge `A -> B`, we must specify:
- caller identity (client),
- required audience,
- required scopes/roles,
- enforcement point (gateway, sidecar, app middleware),
- whether the call crosses a trust boundary.

## Consequences
- Makes auth decisions queryable (who can talk to whom, under what constraints).
- Supports migration away from mTLS by enumerating compensating controls.
- Requires maintaining a policy table as services change.

## Alternatives
- Per-service ad-hoc documentation (rejected: inconsistent and incomplete).
- Rely solely on code and IAM configuration (rejected: hard to audit holistically).

## Knowledge Graph Notes (Structured)
The goal is to represent authentication/authorization as edges with attributes.

### Entities
Services:
- Service: API Gateway (id: `api-gateway`)
- Service: Order Service (id: `order-service`)
- Service: Inventory Service (id: `inventory-service`)
- Service: Billing Service (id: `billing-service`)
- Service: Notification Service (id: `notification-service`)

Identities:
- Client: `order-service-client`
- Client: `api-gateway-client`

Policies:
- Scope: `orders:read`
- Scope: `orders:write`
- Scope: `inventory:reserve`

Trust boundaries:
- Boundary: `external-to-internal`
- Boundary: `internal-mesh`

### Relationships
Authentication mechanism:
- Internal service-to-service AUTHENTICATED_BY OAuth2 Client Credentials (see ADR-0003)
- mTLS DISALLOWED (see ADR-0007)

Entry point:
- External requests ENTER_THROUGH API Gateway (see ADR-0004)
- API Gateway ENFORCES `external-to-internal` boundary

Allowed calls (examples; replace with real policies):
- API Gateway MAY_CALL Order Service REQUIRES_SCOPE `orders:write`
- Order Service MAY_CALL Inventory Service REQUIRES_SCOPE `inventory:reserve`
- Order Service MAY_CALL Billing Service REQUIRES_SCOPE `orders:write`
- Billing Service MAY_CALL Notification Service REQUIRES_SCOPE `orders:read`

Policy ownership:
- Security Team (id: `security`) OWNS_POLICY `service-call-policy`

## References
- Amends: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md)
- Related: [ADR-0007: Deprecate mTLS](0007-deprecate-mtls-auth.md)
- Related: [ADR-0004: Adopt API Gateway](0004-adopt-api-gateway.md)

## Metadata
- ADR: ADR-0011
- Amends: ADR-0003
- Related ADRs: ADR-0007; ADR-0004
- Service IDs: `api-gateway`; `order-service`; `inventory-service`; `billing-service`; `notification-service`
- Policy IDs: `service-call-policy`; trust boundaries `external-to-internal`; `internal-mesh`
