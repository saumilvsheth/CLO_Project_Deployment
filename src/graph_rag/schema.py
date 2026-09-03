"""Closed list of CLO entity and relationship types the extractor is allowed to use."""

from __future__ import annotations

ENTITY_TYPES = (
    "Person",
    "Organization",
    "CLO",
    "Loan",
    "Tranche",
    "Covenant",
    "Location",
)

RELATIONSHIP_TYPES = (
    "MENTIONS",
    "WORKS_AT",
    "MANAGES",
    "TRUSTEE_OF",
    "CONTAINS",
    "BORROWS",
    "SPONSORS",
    "HAS_TRANCHE",
    "GOVERNED_BY",
    "LOCATED_IN",
    "PART_OF",
)

# (from type, relationship, to type) — used later to constrain extraction.
PATTERNS = (
    ("Person", "WORKS_AT", "Organization"),
    ("Organization", "MANAGES", "CLO"),
    ("Organization", "TRUSTEE_OF", "CLO"),
    ("CLO", "CONTAINS", "Loan"),
    ("Organization", "BORROWS", "Loan"),
    ("Organization", "SPONSORS", "Organization"),
    ("CLO", "HAS_TRANCHE", "Tranche"),
    ("CLO", "GOVERNED_BY", "Covenant"),
    ("Organization", "LOCATED_IN", "Location"),
    ("CLO", "LOCATED_IN", "Location"),
    ("Organization", "PART_OF", "Organization"),
)
