"""Abstract interface for graph storage backends.

This module defines the contract that all graph storage implementations
must follow, enabling support for multiple backends (Memgraph, PostgreSQL, etc.).

Added in AAET-84: Abstract storage interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class GraphStoreInterface(ABC):
    """Abstract base class for graph storage backends.
    
    This interface defines the contract for storing and querying code graph data.
    Implementations can use different backends (Memgraph, PostgreSQL, Neo4j, etc.)
    while maintaining a consistent API.
    
    All methods accept tenant_id for multi-tenant isolation (from AAET-83).
    """

    @abstractmethod
    async def insert_nodes(
        self,
        tenant_id: str,
        nodes: list[dict[str, Any]],
    ) -> None:
        """Insert code nodes into storage.
        
        🔒 SECURITY: Implementations MUST use the tenant_id parameter
        and NEVER trust tenant_id from node dictionaries. This prevents
        multi-tenancy violations where malicious clients could insert
        data into another tenant's namespace.
        
        Args:
            tenant_id: Tenant identifier for data isolation (ALWAYS use this)
            nodes: List of node dictionaries with properties:
                - type: Node type (Function, Class, Module, etc.)
                - name: Node name
                - qualified_name: Fully qualified name
                - file_path: Source file path
                - repo_id: Repository identifier
                - ... other node-specific properties
                Note: Any tenant_id in node dicts MUST be overridden by parameter
        
        Raises:
            ValueError: If tenant_id is empty or nodes are invalid
            StorageError: If insertion fails
        """
        pass

    @abstractmethod
    async def insert_edges(
        self,
        tenant_id: str,
        edges: list[dict[str, Any]],
    ) -> None:
        """Insert relationships between code entities.
        
        🔒 SECURITY: Implementations MUST use the tenant_id parameter
        and NEVER trust tenant_id from edge dictionaries. This prevents
        multi-tenancy violations where malicious clients could insert
        data into another tenant's namespace.
        
        Args:
            tenant_id: Tenant identifier for data isolation (ALWAYS use this)
            edges: List of edge dictionaries with properties:
                - from_node: Source node qualified name
                - to_node: Target node qualified name
                - type: Edge type (CALLS, IMPORTS, DEFINES, etc.)
                - ... other edge-specific properties
                Note: Any tenant_id in edge dicts MUST be overridden by parameter
        
        Raises:
            ValueError: If tenant_id is empty or edges are invalid
            StorageError: If insertion fails
        """
        pass

    @abstractmethod
    async def query_graph(
        self,
        tenant_id: str,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a graph query with tenant isolation enforcement.
        
        🔒 SECURITY: Implementations MUST validate that queries include
        tenant_id filtering to prevent cross-tenant data access. Queries
        that don't include tenant_id filtering MUST be rejected.
        
        For SQL-based implementations:
        - SELECT queries MUST include "WHERE tenant_id = $X"
        - The tenant_id in params MUST match the method parameter
        - Parameterized queries MUST be used (no string interpolation)
        
        Example SAFE query:
            query = "SELECT * FROM code_nodes WHERE tenant_id = $1 AND name = $2"
            params = {"tenant_id": tenant_id, "name": "MyClass"}
        
        Example UNSAFE queries (MUST be rejected):
            query = "SELECT * FROM code_nodes"  # No tenant_id filtering
            query = "SELECT * FROM code_nodes WHERE name = 'test'"  # No tenant_id
        
        Args:
            tenant_id: Tenant identifier for data isolation
            query: Query string (format depends on backend, MUST include tenant filtering)
            params: Query parameters (MUST include tenant_id matching parameter)
        
        Returns:
            List of result dictionaries
        
        Raises:
            ValueError: If tenant_id is empty or query is invalid
            StorageError: If query doesn't include tenant filtering or execution fails
        """
        pass

    @abstractmethod
    async def delete_nodes(
        self,
        tenant_id: str,
        node_filter: dict[str, Any],
    ) -> int:
        """Delete nodes matching the filter.
        
        Args:
            tenant_id: Tenant identifier for data isolation
            node_filter: Filter criteria (e.g., {"file_path": "src/main.py"})
        
        Returns:
            Number of nodes deleted
        
        Raises:
            ValueError: If tenant_id is empty
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def delete_edges(
        self,
        tenant_id: str,
        edge_filter: dict[str, Any],
    ) -> int:
        """Delete edges matching the filter.
        
        Args:
            tenant_id: Tenant identifier for data isolation
            edge_filter: Filter criteria
        
        Returns:
            Number of edges deleted
        
        Raises:
            ValueError: If tenant_id is empty
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def get_node(
        self,
        tenant_id: str,
        qualified_name: str,
    ) -> dict[str, Any] | None:
        """Get a single node by qualified name.
        
        Args:
            tenant_id: Tenant identifier for data isolation
            qualified_name: Fully qualified name of the node
        
        Returns:
            Node dictionary if found, None otherwise
        
        Raises:
            ValueError: If tenant_id is empty
            StorageError: If query fails
        """
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        tenant_id: str,
        qualified_name: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """Get neighboring nodes connected by edges.
        
        Args:
            tenant_id: Tenant identifier for data isolation
            qualified_name: Fully qualified name of the source node
            edge_type: Optional edge type filter (CALLS, IMPORTS, etc.)
            direction: "outgoing", "incoming", or "both"
        
        Returns:
            List of neighboring node dictionaries
        
        Raises:
            ValueError: If tenant_id is empty or direction is invalid
            StorageError: If query fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection and release resources.
        
        Should be called when the store is no longer needed.
        """
        pass


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass
