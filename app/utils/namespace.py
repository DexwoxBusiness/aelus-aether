from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status

ALLOWED_TYPES = ("code", "docs", "stories")

NamespaceType = Literal["code", "docs", "stories"]
_NAMESPACE_RE = re.compile(
    r"^(?P<tenant>[0-9a-fA-F-]{36}):(?P<org>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+):(?P<branch>[A-Za-z0-9._/\-]+):(?P<type>code|docs|stories)$"
)


@dataclass(frozen=True)
class NamespaceComponents:
    tenant_id: UUID
    org: str
    repo: str
    branch: str
    type: NamespaceType

    @property
    def full(self) -> str:
        return f"{self.tenant_id}:{self.org}/{self.repo}:{self.branch}:{self.type}"


def parse_namespace(namespace: str) -> NamespaceComponents:
    m = _NAMESPACE_RE.match(namespace or "")
    if not m:
        raise ValueError(
            "Invalid namespace format. Expected {tenant_id}:{org}/{repo}:{branch}:{type} with type in {code,docs,stories}."
        )
    tenant_raw = m.group("tenant")
    try:
        tenant_id = UUID(tenant_raw)
    except ValueError as e:
        raise ValueError(f"Invalid tenant_id format in namespace: {tenant_raw}") from e
    type_val = m.group("type")
    if type_val not in ALLOWED_TYPES:
        raise ValueError(f"Invalid namespace type: {type_val}. Must be one of {ALLOWED_TYPES}")

    # Explicit type narrowing for NamespaceType
    if type_val == "code":
        ns_type: NamespaceType = "code"
    elif type_val == "docs":
        ns_type = "docs"
    else:  # "stories"
        ns_type = "stories"
    return NamespaceComponents(
        tenant_id=tenant_id,
        org=m.group("org"),
        repo=m.group("repo"),
        branch=m.group("branch"),
        type=ns_type,
    )


def validate_namespace_for_tenant(namespace: str, expected_tenant_id: UUID) -> NamespaceComponents:
    comp = parse_namespace(namespace)
    if comp.tenant_id != expected_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Namespace tenant_id does not match authenticated tenant.",
        )
    return comp
