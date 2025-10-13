"""PostgreSQL implementation of GraphStoreInterface.

This module provides a PostgreSQL-based storage backend for code graph data.
Uses asyncpg for async database operations.

Added in AAET-84: PostgreSQL graph store implementation.
"""

import json
from typing import Any

try:
    import asyncpg
except ImportError:
    asyncpg = None  # Optional dependency

from .interface import GraphStoreInterface, StorageError


class PostgresGraphStore(GraphStoreInterface):
    """PostgreSQL implementation of graph storage.
    
    Stores nodes and edges in PostgreSQL tables with JSONB columns for
    flexible schema. Provides efficient querying with indexes on tenant_id
    and qualified_name.
    
    Schema:
        code_nodes (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            repo_id VARCHAR(36) NOT NULL,
            qualified_name TEXT NOT NULL,
            node_type VARCHAR(50) NOT NULL,
            properties JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tenant_id, repo_id, qualified_name)
        )
        
        code_edges (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            from_node TEXT NOT NULL,
            to_node TEXT NOT NULL,
            edge_type VARCHAR(50) NOT NULL,
            properties JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(tenant_id, from_node, to_node, edge_type)
        )
    """

    def __init__(self, connection_string: str):
        """Initialize PostgreSQL store.
        
        Args:
            connection_string: PostgreSQL connection string
                Example: "postgresql://user:pass@localhost/dbname"
        
        Raises:
            ImportError: If asyncpg is not installed
        """
        if asyncpg is None:
            raise ImportError(
                "asyncpg is required for PostgresGraphStore. "
                "Install it with: pip install asyncpg"
            )
        
        self.connection_string = connection_string
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.connection_string)

    async def _ensure_connected(self) -> None:
        """Ensure connection pool is established."""
        if self.pool is None:
            await self.connect()

    async def insert_nodes(
        self,
        tenant_id: str,
        nodes: list[dict[str, Any]],
    ) -> None:
        """Insert code nodes into PostgreSQL.
        
        Uses UPSERT (INSERT ... ON CONFLICT) to handle duplicates.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        if not nodes:
            return  # Nothing to insert
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # Prepare data for batch insert
                values = [
                    (
                        node.get("tenant_id", tenant_id),
                        node.get("repo_id"),
                        node.get("qualified_name"),
                        node.get("type"),
                        json.dumps(node),  # Store full node as JSONB
                    )
                    for node in nodes
                ]
                
                # Batch insert with UPSERT
                await conn.executemany(
                    """
                    INSERT INTO code_nodes 
                        (tenant_id, repo_id, qualified_name, node_type, properties)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (tenant_id, repo_id, qualified_name)
                    DO UPDATE SET
                        node_type = EXCLUDED.node_type,
                        properties = EXCLUDED.properties,
                        updated_at = NOW()
                    """,
                    values,
                )
        except Exception as e:
            raise StorageError(f"Failed to insert nodes: {e}") from e

    async def insert_edges(
        self,
        tenant_id: str,
        edges: list[dict[str, Any]],
    ) -> None:
        """Insert edges into PostgreSQL.
        
        Uses UPSERT (INSERT ... ON CONFLICT) to handle duplicates.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        if not edges:
            return  # Nothing to insert
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # Prepare data for batch insert
                values = [
                    (
                        edge.get("tenant_id", tenant_id),
                        edge.get("from_node"),
                        edge.get("to_node"),
                        edge.get("type"),
                        json.dumps(edge),  # Store full edge as JSONB
                    )
                    for edge in edges
                ]
                
                # Batch insert with UPSERT
                await conn.executemany(
                    """
                    INSERT INTO code_edges 
                        (tenant_id, from_node, to_node, edge_type, properties)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (tenant_id, from_node, to_node, edge_type)
                    DO UPDATE SET
                        properties = EXCLUDED.properties,
                        updated_at = NOW()
                    """,
                    values,
                )
        except Exception as e:
            raise StorageError(f"Failed to insert edges: {e}") from e

    async def query_graph(
        self,
        tenant_id: str,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query against the graph.
        
        Note: This is a raw SQL query interface. For production use,
        consider adding a query builder or using an ORM.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # Add tenant_id to params if not present
                query_params = params or {}
                if "tenant_id" not in query_params:
                    query_params["tenant_id"] = tenant_id
                
                # Execute query
                rows = await conn.fetch(query, *query_params.values())
                
                # Convert rows to dictionaries
                return [dict(row) for row in rows]
        except Exception as e:
            raise StorageError(f"Query failed: {e}") from e

    async def delete_nodes(
        self,
        tenant_id: str,
        node_filter: dict[str, Any],
    ) -> int:
        """Delete nodes matching the filter."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # Build WHERE clause from filter
                conditions = ["tenant_id = $1"]
                params = [tenant_id]
                
                for i, (key, value) in enumerate(node_filter.items(), start=2):
                    if key == "file_path":
                        conditions.append(f"properties->>'file_path' = ${i}")
                        params.append(value)
                    elif key == "qualified_name":
                        conditions.append(f"qualified_name = ${i}")
                        params.append(value)
                
                where_clause = " AND ".join(conditions)
                query = f"DELETE FROM code_nodes WHERE {where_clause}"
                
                result = await conn.execute(query, *params)
                # Extract count from result string like "DELETE 5"
                return int(result.split()[-1]) if result else 0
        except Exception as e:
            raise StorageError(f"Failed to delete nodes: {e}") from e

    async def delete_edges(
        self,
        tenant_id: str,
        edge_filter: dict[str, Any],
    ) -> int:
        """Delete edges matching the filter."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # Build WHERE clause from filter
                conditions = ["tenant_id = $1"]
                params = [tenant_id]
                
                for i, (key, value) in enumerate(edge_filter.items(), start=2):
                    if key in ("from_node", "to_node", "edge_type"):
                        conditions.append(f"{key} = ${i}")
                        params.append(value)
                
                where_clause = " AND ".join(conditions)
                query = f"DELETE FROM code_edges WHERE {where_clause}"
                
                result = await conn.execute(query, *params)
                return int(result.split()[-1]) if result else 0
        except Exception as e:
            raise StorageError(f"Failed to delete edges: {e}") from e

    async def get_node(
        self,
        tenant_id: str,
        qualified_name: str,
    ) -> dict[str, Any] | None:
        """Get a single node by qualified name."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT properties
                    FROM code_nodes
                    WHERE tenant_id = $1 AND qualified_name = $2
                    """,
                    tenant_id,
                    qualified_name,
                )
                
                if row:
                    return json.loads(row["properties"])
                return None
        except Exception as e:
            raise StorageError(f"Failed to get node: {e}") from e

    async def get_neighbors(
        self,
        tenant_id: str,
        qualified_name: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """Get neighboring nodes connected by edges."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        if direction not in ("outgoing", "incoming", "both"):
            raise ValueError(f"Invalid direction: {direction}")
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # Build query based on direction
                if direction == "outgoing":
                    query = """
                        SELECT n.properties
                        FROM code_edges e
                        JOIN code_nodes n ON e.to_node = n.qualified_name
                        WHERE e.tenant_id = $1 
                          AND e.from_node = $2
                          AND n.tenant_id = $1
                    """
                elif direction == "incoming":
                    query = """
                        SELECT n.properties
                        FROM code_edges e
                        JOIN code_nodes n ON e.from_node = n.qualified_name
                        WHERE e.tenant_id = $1 
                          AND e.to_node = $2
                          AND n.tenant_id = $1
                    """
                else:  # both
                    query = """
                        SELECT n.properties
                        FROM code_edges e
                        JOIN code_nodes n ON (
                            (e.to_node = n.qualified_name AND e.from_node = $2)
                            OR (e.from_node = n.qualified_name AND e.to_node = $2)
                        )
                        WHERE e.tenant_id = $1 AND n.tenant_id = $1
                    """
                
                # Add edge type filter if specified
                params = [tenant_id, qualified_name]
                if edge_type:
                    query += " AND e.edge_type = $3"
                    params.append(edge_type)
                
                rows = await conn.fetch(query, *params)
                return [json.loads(row["properties"]) for row in rows]
        except Exception as e:
            raise StorageError(f"Failed to get neighbors: {e}") from e

    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
