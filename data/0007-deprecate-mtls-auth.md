# File: 0006-logging-and-observability.md

# ADR-0007: Deprecate mTLS Authentication

Status: Accepted  
Date: 2023-09-12  
Amends: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md)

## Context
Some legacy services still use mTLS alongside OAuth2. Maintaining dual mechanisms increases complexity. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Deprecate mTLS in favor of OAuth2-only authentication.

## Consequences
- Simplifies service-to-service security.  
- Breaks backward compatibility with some legacy clients.  
- Migration path required for services still using mTLS.  

## Alternatives
- Keep dual approach (rejected: too complex).  

## References
- [NIST mTLS Guidance](https://csrc.nist.gov/publications/detail/sp/800-63/3/final)  
- Amends: [ADR-0003](0003-service-to-service-authentication.md)  