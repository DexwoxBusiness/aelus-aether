"""Graph service protocol for code_graph_rag library.

This module provides a protocol/interface for graph database operations.
The original code-graph-rag used Memgraph, but this can be adapted to any graph store.
"""

from typing import Any, Protocol


class MemgraphIngestor(Protocol):
    """Protocol for graph database ingestion operations.

    This is a structural type (Protocol) that defines the interface
    for graph operations. Implementations can use any graph database
    (Memgraph, Neo4j, PostgreSQL with graph extensions, etc.).
    """

    def ensure_node_batch(
        self,
        node_type: str,
        properties: dict[str, Any],
    ) -> None:
        """Ensure a node exists in the graph with given properties.

        Args:
            node_type: Type/label of the node (e.g., "Function", "Class")
            properties: Dictionary of node properties
        """
        ...

    def ensure_relationship_batch(
        self,
        from_node: tuple[str, str, Any],
        relationship_type: str,
        to_node: tuple[str, str, Any],
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Ensure a relationship exists between two nodes.

        Args:
            from_node: Tuple of (node_type, property_key, property_value) for source node
            relationship_type: Type of relationship (e.g., "CALLS", "INHERITS")
            to_node: Tuple of (node_type, property_key, property_value) for target node
            properties: Optional properties for the relationship
        """
        ...

    def flush_all(self) -> None:
        """Flush all pending batch operations to the database."""
        ...

    def set_tenant_id(self, tenant_id: str) -> None:
        """Set the tenant ID for multi-tenant operations.

        Args:
            tenant_id: Unique identifier for the tenant
        """
        ...
