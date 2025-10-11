from typing import Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GraphData(BaseModel):
    """Data model for results returned from the knowledge graph tool."""

    query_used: str
    results: list[dict[str, Any]]
    summary: str = Field(description="A brief summary of the operation's outcome.")

    @field_validator("results", mode="before")
    @classmethod
    def _format_results(cls, v: Any) -> list[dict[str, Any]]:
        if not isinstance(v, list):
            return []  # Return empty list instead of v

        clean_results = []
        for row in v:
            clean_row = {}
            for k, val in row.items():
                if not isinstance(
                    val, str | int | float | bool | list | dict | type(None)
                ):
                    clean_row[k] = str(val)
                else:
                    clean_row[k] = val  # type: ignore
            clean_results.append(clean_row)
        return clean_results

    model_config = ConfigDict(extra="forbid")


class CodeSnippet(BaseModel):
    """Data model for code snippet results."""

    qualified_name: str
    source_code: str
    file_path: str
    line_start: int
    line_end: int
    docstring: str | None = None
    found: bool = True
    error_message: str | None = None


class ShellCommandResult(BaseModel):
    """Data model for shell command results."""

    return_code: int
    stdout: str
    stderr: str


# ============================================================================
# Multi-tenant Code Graph Schemas (Added in AAET-83)
# ============================================================================


class NodeType(str, Enum):
    """Types of code nodes."""

    FUNCTION = "Function"
    CLASS = "Class"
    METHOD = "Method"
    MODULE = "Module"
    FILE = "File"
    INTERFACE = "Interface"
    ENUM = "Enum"
    STRUCT = "Struct"
    TRAIT = "Trait"
    VARIABLE = "Variable"


class EdgeType(str, Enum):
    """Types of relationships between code nodes."""

    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    DEFINES = "DEFINES"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    USES_API = "USES_API"
    CONTAINS = "CONTAINS"


class ParsedNode(BaseModel):
    """
    Represents a code entity (function, class, method, etc.) with tenant context.
    
    Added in AAET-83: tenant_id and repo_id for multi-tenant isolation.
    """

    # Tenant context (AAET-83)
    tenant_id: UUID | str
    repo_id: UUID | str

    # Node identity
    node_type: NodeType
    qualified_name: str
    name: str

    # Location
    file_path: str
    start_line: int | None = None
    end_line: int | None = None

    # Code content
    source_code: str | None = None
    signature: str | None = None
    docstring: str | None = None

    # Metadata
    language: str | None = None
    complexity: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ParsedEdge(BaseModel):
    """
    Represents a relationship between code entities with tenant context.
    
    Added in AAET-83: tenant_id for multi-tenant isolation.
    """

    # Tenant context (AAET-83)
    tenant_id: UUID | str

    # Edge identity
    from_node: str  # qualified_name of source node
    to_node: str  # qualified_name of target node
    edge_type: EdgeType

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ParsedFile(BaseModel):
    """
    Represents a parsed file with all its nodes and edges.
    
    Added in AAET-83: tenant_id and repo_id for multi-tenant isolation.
    """

    # Tenant context (AAET-83)
    tenant_id: UUID | str
    repo_id: UUID | str

    # File identity
    file_path: str
    language: str

    # Parsed content
    nodes: list[ParsedNode] = Field(default_factory=list)
    edges: list[ParsedEdge] = Field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")
