from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class Namespace(BaseModel):
    """Pydantic model for validated namespace.

    Accepts either a full namespace string via `namespace`, or a dict with
    explicit fields. It normalizes into explicit fields for downstream use.

    Format: {tenant_id}:{org}/{repo}:{branch}:{type}
    where type in {code, docs, stories}.
    """

    namespace: str = Field(..., description="{tenant}:{org}/{repo}:{branch}:{type}")
    tenant_id: UUID
    org: str
    repo: str
    branch: str
    type: Literal["code", "docs", "stories"]

    @model_validator(mode="before")
    @classmethod
    def parse_namespace(cls, data: Any) -> Any:
        if isinstance(data, dict) and "namespace" in data:
            from app.utils.namespace import parse_namespace

            ns = parse_namespace(str(data["namespace"]))
            # Merge parsed fields back
            return {
                **data,
                "tenant_id": ns.tenant_id,
                "org": ns.org,
                "repo": ns.repo,
                "branch": ns.branch,
                "type": ns.type,
            }
        return data

    def validate_for_tenant(self, expected_tenant: UUID) -> None:
        """Ensure tenant in namespace matches expected tenant."""
        if self.tenant_id != expected_tenant:
            raise PermissionError("Namespace tenant_id does not match authenticated tenant.")
