# File: 0004-adopt-api-gateway.md

# ADR-0004: Adopt API Gateway for External Traffic

Status: Accepted  
Date: 2023-02-15  

## Context
Clients need a single entry point to backend services. We also want to enforce cross-cutting concerns like rate limiting and authentication. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Adopt Kong API Gateway as the single entry point for all external client requests.

## Consequences
- Simplified external integration.  
- Centralized enforcement of authentication.  
- Introduces single point of failure (must ensure HA setup).  

## Alternatives
- No gateway, expose services directly (rejected: inconsistent policies).  
- Envoy proxy only (rejected: limited ecosystem plugins).  

## References
- [Kong Gateway Docs](https://docs.konghq.com/)  
- Related: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md)  