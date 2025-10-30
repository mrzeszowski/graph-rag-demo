from neo4j_graphrag.experimental.pipeline.types.schema import (
    EntityInputType,
    RelationInputType,
)

NODE_TYPES: list[EntityInputType] = [
    {
        "label": "Decision",
        "description": "Architecture Decision Record (ADR)",
        "properties": [
            {"name": "adr_num", "type": "STRING"},
            {"name": "title", "type": "STRING"},
            {"name": "status", "type": "STRING"},      # e.g., Accepted, Superseded, Proposed
            {"name": "date", "type": "DATE"},
            {"name": "file", "type": "STRING"},        # md filename
        ],
    },
    {"label": "Component", "properties": [
        {"name": "name", "type": "STRING"},           # e.g., Order Service, API Gateway
        {"name": "kind", "type": "STRING"},           # service|gateway|db|infra (optional hint)
    ]},
    {"label": "Capability", "properties": [
        {"name": "name", "type": "STRING"}            # business/domain capability
    ]},
    {"label": "Technology", "properties": [
        {"name": "name", "type": "STRING"},           # Kafka, Pub/Sub, Keycloak, ELK, Prometheus
        {"name": "category", "type": "STRING"},       # messaging|idp|logging|metrics|gateway
        {"name": "vendor", "type": "STRING"},
    ]},
    {"label": "Team", "properties": [
        {"name": "name", "type": "STRING"}            # Platform Team, Architecture Guild
    ]},
    {"label": "Option", "properties": [
        {"name": "name", "type": "STRING"},           # mTLS, API Keys, etc.
        {"name": "selected", "type": "BOOLEAN"},      # convenience flag for summarization
    ]},
    {"label": "APIEndpoint", "properties": [
        {"name": "path", "type": "STRING"},           # /orders/{id}
        {"name": "method", "type": "STRING"},         # GET/POST (optional)
    ]},
    {"label": "EventStream", "properties": [
        {"name": "name", "type": "STRING"},           # topic/queue name
        {"name": "kind", "type": "STRING"},           # topic|queue
    ]},
    {"label": "DataAsset", "properties": [
        {"name": "name", "type": "STRING"},           # DB/schema/table name
        {"name": "engine", "type": "STRING"},         # PostgreSQL, etc.
    ]},
    {"label": "Doc", "properties": [
        {"name": "title", "type": "STRING"},
        {"name": "url", "type": "STRING"},
    ]},
]

RELATIONSHIP_TYPES: list[RelationInputType] = [
    "SUPERSEDES",          # Decision -> Decision
    "AMENDS",              # Decision -> Decision
    "RELATED_TO",          # Decision -> Decision
    "DECIDES_ON",          # Decision -> Component|Capability
    "SELECTS",             # Decision -> Option
    "CONSIDERED",          # Decision -> Option
    "USES",                # Decision|Component -> Technology
    "AFFECTS",             # Decision -> Component|Capability
    "REVIEWED_BY",         # Decision -> Team
    "EXPOSES",             # Decision -> APIEndpoint
    "PRODUCES",            # Component -> EventStream
    "CONSUMES",            # Component -> EventStream
    "CITES",               # Decision -> Doc
]

PATTERNS = [
    # Decision lifecycle & cross-links
    ("Decision", "SUPERSEDES", "Decision"),
    ("Decision", "AMENDS", "Decision"),
    ("Decision", "RELATED_TO", "Decision"),

    # Scope & impact
    ("Decision", "DECIDES_ON", "Component"),
    ("Decision", "DECIDES_ON", "Capability"),
    ("Decision", "AFFECTS", "Component"),
    ("Decision", "AFFECTS", "Capability"),

    # Alternatives & choice
    ("Decision", "CONSIDERED", "Option"),
    ("Decision", "SELECTS", "Option"),

    # Technology usage (both direct decision and concrete component usage)
    ("Decision", "USES", "Technology"),
    ("Component", "USES", "Technology"),

    # API and eventing surface
    ("Decision", "EXPOSES", "APIEndpoint"),
    ("Component", "PRODUCES", "EventStream"),
    ("Component", "CONSUMES", "EventStream"),

    # Governance / references
    ("Decision", "REVIEWED_BY", "Team"),
    ("Decision", "CITES", "Doc"),
]