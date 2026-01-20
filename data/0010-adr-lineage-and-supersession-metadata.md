# File: 0010-adr-lineage-and-supersession-metadata.md

# ADR-0010: Establish ADR Lineage (Supersedes/Amends) Metadata

Status: Accepted  
Date: 2024-01-17  
Related: [ADR-0001: Use Kafka for Event Streaming](0001-use-kafka-for-event-streaming.md), [ADR-0005: Switch to Cloud Pub/Sub](0005-switch-to-cloud-pubsub.md)

## Context
Teams frequently ask “what is the current decision?” and “what changed over time?”. In practice, older ADRs still show up in search results and can be mistaken for current guidance unless the lineage is explicit and queryable. This document is created in answer for needs of 'System Knowledge Graph'.

## Decision
Make ADR lineage metadata mandatory and consistent.

Every ADR must include (when applicable):
- `Supersedes:` and/or `Superseded by:` links
- `Amends:` and/or `Amended by:` links
- `Related:` links

Additionally, each ADR must include a short “Rationale Delta” section when it supersedes/amends another ADR, describing what changed and why.

## Consequences
- Easier to answer “current state” questions by following the lineage chain.
- Better change traceability (what decision forced what downstream changes).
- Slightly more authoring work for ADR writers.

## Alternatives
- Keep lineage in people’s heads (rejected: doesn’t scale).
- Encode lineage only in the title (rejected: too ambiguous, not structured).

## Knowledge Graph Notes (Structured)
These relationships are first-class edges in the knowledge graph.

### Entities
- ADR: `ADR-0001`
- ADR: `ADR-0005`
- ADR: `ADR-0007`
- ADR: `ADR-0008`
- Topic: `event-streaming-platform`
- Topic: `service-to-service-auth`
- Topic: `event-schema-governance`

### Relationships
Lineage:
- `ADR-0005` SUPERSEDES `ADR-0001`
- `ADR-0007` AMENDS `ADR-0003`

“Current for topic” (derived from lineage, but can be asserted for clarity):
- `ADR-0005` GOVERNS `event-streaming-platform`
- `ADR-0003` GOVERNS `service-to-service-auth`
- `ADR-0007` REFINES `service-to-service-auth`
- `ADR-0008` GOVERNS `event-schema-governance`

Rationale links:
- `ADR-0005` MOTIVATED_BY `operational-overhead`
- `ADR-0001` ENABLED `event-replay`

## References
 - Example lineage pair: [ADR-0001: Use Kafka for Event Streaming](0001-use-kafka-for-event-streaming.md) → [ADR-0005: Switch to Cloud Pub/Sub](0005-switch-to-cloud-pubsub.md)
- Related: [ADR-0003: Service-to-Service Authentication](0003-service-to-service-authentication.md), [ADR-0007: Deprecate mTLS](0007-deprecate-mtls-auth.md)
- Related: [ADR-0008: Introduce Schema Registry](0008-event-schema-registry.md)

## Metadata
- ADR: ADR-0010
- Decision: Lineage metadata is mandatory
- Relationship types: SUPERSEDES; AMENDS; RELATED_TO
- Requires section: Rationale Delta (for supersedes/amends)
- Related ADRs: ADR-0001; ADR-0005; ADR-0003; ADR-0007; ADR-0008
