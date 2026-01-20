# File: 0003-service-to-service-authentication.md

# ADR-0003: Service-to-Service Authentication with OAuth2

Status: Accepted  
Date: 2023-01-20  
Amended by: [ADR-0007: Deprecate mTLS Authentication](0007-deprecate-mtls-auth.md)

## Context
Microservices must authenticate and authorize each other securely. Options include mutual TLS, API keys, or OAuth2 flows. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Use OAuth2 Client Credentials flow with Keycloak as the Identity Provider (IdP). Tokens will be injected by sidecar proxies at runtime.

## Consequences
- Centralized control over credentials.  
- Services require token validation libraries.  
- Periodic key rotation required.  

## Alternatives
- mTLS (considered, but operationally complex).  
- API Keys (insufficient for fine-grained access).  

## References
- [RFC 6749: OAuth 2.0](https://www.rfc-editor.org/rfc/rfc6749)  
- [Keycloak Documentation](https://www.keycloak.org/documentation)  
- Related: [ADR-0007: Deprecate mTLS](0007-deprecate-mtls-auth.md)  

## Metadata
- ADR: ADR-0003
- Amended by: ADR-0007
- Affects components: All microservices
- Uses technology: Keycloak
- Selected option: OAuth2 Client Credentials
- Considered options: mTLS; API Keys