"""Abstract interface for graph storage backends.

This module defines the contract that all graph storage implementations
must follow. Currently supports PostgreSQL with potential for future backends.

Added in AAET-84: Abstract storage interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class GraphStoreInterface(ABC):
    """Abstract base class for graph storage backends.
    
    This interface defines the contract for storing and querying code graph data.
    Currently implemented for PostgreSQL, with potential for future backends.
    
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

    # AAET-85: Batch methods for compatibility with processor pattern
    def ensure_node_batch(self, node_type: str, properties: dict[str, Any]) -> None:
        """Queue a node for batch insertion (sync method for compatibility).
        
        Added in AAET-85: Compatibility method for processors that use batching.
        This is a synchronous method that queues nodes for later async insertion.
        
        Args:
            node_type: Type of node (Function, Class, Module, etc.)
            properties: Node properties including qualified_name, name, etc.
        
        Note: Actual insertion happens when flush is called or batch is full.
        """
        pass

    def ensure_relationship_batch(
        self,
        from_node: tuple[str, str, str],
        edge_type: str,
        to_node: tuple[str, str, str],
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Queue a relationship for batch insertion (sync method for compatibility).
        
        Added in AAET-85: Compatibility method for processors that use batching.
        This is a synchronous method that queues edges for later async insertion.
        
        Args:
            from_node: Tuple of (node_type, key_field, key_value) for source
            edge_type: Type of relationship (CALLS, IMPORTS, DEFINES, etc.)
            to_node: Tuple of (node_type, key_field, key_value) for target
            properties: Optional edge properties
        
        Note: Actual insertion happens when flush is called or batch is full.
        """
        pass
    
    @abstractmethod
    async def count_nodes(self, tenant_id: str, repo_id: str | None = None) -> int:
        """Count nodes for a tenant, optionally filtered by repository.
        
        Added in AAET-86: For metrics collection.
        
        Args:
            tenant_id: Tenant identifier
            repo_id: Optional repository identifier to filter by
        
        Returns:
            Number of nodes matching the criteria
        
        Raises:
            StorageError: If count operation fails
        """
        pass
    
    @abstractmethod
    async def count_edges(
        self,
        tenant_id: str,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: str | None = None
    ) -> int:
        """Count edges matching the given criteria.
        
        Args:
            tenant_id: Tenant identifier for isolation
            source_id: Optional source node ID to filter by
            target_id: Optional target node ID to filter by
            edge_type: Optional edge type to filter by
        
        Returns:
            Number of edges matching the criteria
        
        Raises:
            StorageError: If count operation fails
        """
        pass
    
    @abstractmethod
    async def insert_embeddings(
        self,
        tenant_id: str,
        repo_id: str,
        embeddings: list[dict[str, Any]]
    ) -> int:
        """Insert embeddings into storage.
        
        Required by JIRA AAET-87 for embedding service integration.
        Supports multi-tenant and multi-repository isolation.
        
        Args:
            tenant_id: Tenant identifier for isolation
            repo_id: Repository identifier for isolation
            embeddings: List of embedding dictionaries with keys:
                - chunk_id: Unique identifier for the chunk
                - embedding: Vector embedding (list of floats)
                - metadata: Optional metadata dict
        
        Returns:
            Number of embeddings inserted
        
        Raises:
            StorageError: If insertion fails
        """
        pass
    
    @abstractmethod
    async def query_embeddings(
        self,
        tenant_id: str,
        repo_id: str | None = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Query embeddings with optional repository filtering.
        
        Args:
            tenant_id: Tenant identifier for isolation
            repo_id: Optional repository identifier to filter by specific repo
            limit: Maximum number of embeddings to return
        
        Returns:
            List of embedding dictionaries
        
        Raises:
            StorageError: If query fails
        """
        pass
    
    @abstractmethod
    async def search_similar_embeddings(
        self,
        tenant_id: str,
        query_embedding: list[float],
        repo_id: str | None = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search for similar embeddings using vector similarity.
        
        Args:
            tenant_id: Tenant identifier for isolation
            query_embedding: Query vector to find similar embeddings
            repo_id: Optional repository identifier to filter by specific repo
            limit: Maximum number of results to return
        
        Returns:
            List of similar embeddings with similarity scores
        
        Raises:
            StorageError: If search fails
        """
        pass


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass
