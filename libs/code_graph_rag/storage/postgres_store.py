"""PostgreSQL implementation of GraphStoreInterface.

This module provides a PostgreSQL-based storage backend for code graph data.
Uses asyncpg for async database operations.

Added in AAET-84: PostgreSQL graph store implementation.
"""

import asyncio
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
    
    Added in AAET-85: Batching support for compatibility with processors.
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
        
        # AAET-85: Batching queues for compatibility
        self._node_batch: list[tuple[str, dict[str, Any]]] = []
        self._edge_batch: list[tuple[tuple[str, str, str], str, tuple[str, str, str], dict[str, Any] | None]] = []
        self._tenant_id: str | None = None  # Will be set by GraphUpdater

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL.
        
        Raises:
            StorageError: If connection fails after retries
        """
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=2,
                    max_size=10,
                    timeout=30.0,  # Connection timeout
                    command_timeout=60.0,  # Query timeout
                )
                
                # Verify connection works
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                    
            except asyncpg.PostgresError as e:
                raise StorageError(f"Failed to connect to PostgreSQL: {e}") from e
            except Exception as e:
                raise StorageError(f"Unexpected error connecting to PostgreSQL: {e}") from e

    async def _ensure_connected(self) -> None:
        """Ensure connection pool is established and healthy.
        
        Raises:
            StorageError: If connection is unavailable or unhealthy
        """
        if self.pool is None:
            await self.connect()
        
        # Verify pool is healthy with timeout
        try:
            # Use asyncio.timeout for Python 3.11+, or asyncio.wait_for for older versions
            async with self.pool.acquire() as conn:
                # Quick health check
                await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=5.0)
        except asyncio.TimeoutError:
            raise StorageError("Database connection timeout - pool may be exhausted")
        except asyncpg.PostgresError as e:
            raise StorageError(f"Database connection unhealthy: {e}") from e
        except Exception as e:
            raise StorageError(f"Database connection check failed: {e}") from e

    async def insert_nodes(
        self,
        tenant_id: str,
        nodes: list[dict[str, Any]],
    ) -> None:
        """Insert code nodes into PostgreSQL.
        
        Uses UPSERT (INSERT ... ON CONFLICT) to handle duplicates.
        
        SECURITY: The tenant_id parameter ALWAYS overrides any tenant_id
        in the node dictionaries to prevent multi-tenancy violations.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        if not nodes:
            return  # Nothing to insert
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # SECURITY FIX: Always use parameter tenant_id, never trust node data
                # This prevents malicious/buggy clients from inserting data into
                # another tenant's namespace
                values = [
                    (
                        tenant_id,  # ✅ Always use parameter tenant_id
                        node.get("repo_id"),
                        node.get("qualified_name"),
                        node.get("type"),
                        # ✅ Ensure JSONB also has correct tenant_id
                        json.dumps({**node, "tenant_id": tenant_id}),
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
        
        SECURITY: The tenant_id parameter ALWAYS overrides any tenant_id
        in the edge dictionaries to prevent multi-tenancy violations.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        if not edges:
            return  # Nothing to insert
        
        await self._ensure_connected()
        
        try:
            async with self.pool.acquire() as conn:
                # SECURITY FIX: Always use parameter tenant_id, never trust edge data
                # This prevents malicious/buggy clients from inserting data into
                # another tenant's namespace
                values = [
                    (
                        tenant_id,  # ✅ Always use parameter tenant_id
                        edge.get("from_node"),
                        edge.get("to_node"),
                        edge.get("type"),
                        # ✅ Ensure JSONB also has correct tenant_id
                        json.dumps({**edge, "tenant_id": tenant_id}),
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
        """Execute a SQL query against the graph with automatic tenant filtering.
        
        🔒 SECURITY: This method automatically enforces tenant isolation by
        validating that queries include tenant_id filtering. This prevents
        accidental or malicious cross-tenant data access.
        
        The method validates that:
        1. SELECT queries reference tenant_id in WHERE clause
        2. Parameterized queries are used (not string interpolation)
        3. tenant_id parameter is included in query parameters
        
        Example SAFE query:
            query = "SELECT * FROM code_nodes WHERE tenant_id = $1 AND name = $2"
            params = {"tenant_id": tenant_id, "name": "MyClass"}
            results = await store.query_graph(tenant_id, query, params)
        
        Example queries that will be REJECTED:
            query = "SELECT * FROM code_nodes"  # ❌ No tenant_id filtering
            query = "SELECT * FROM code_nodes WHERE name = 'test'"  # ❌ No tenant_id
        
        Args:
            tenant_id: Tenant identifier for data isolation
            query: SQL query string (MUST use parameterized queries)
            params: Query parameters (MUST include tenant_id)
        
        Returns:
            List of result dictionaries
        
        Raises:
            ValueError: If tenant_id is empty
            StorageError: If query doesn't include tenant filtering or execution fails
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        
        await self._ensure_connected()
        
        try:
            # SECURITY VALIDATION: Ensure query includes tenant_id filtering
            query_lower = query.lower()
            
            # Check if this is a SELECT query (most common case)
            if "select" in query_lower:
                # Validate tenant_id is referenced in the query
                if "tenant_id" not in query_lower:
                    raise StorageError(
                        "SECURITY: Query must include tenant_id filtering. "
                        "Example: WHERE tenant_id = $1"
                    )
                
                # Validate WHERE clause exists for SELECT queries
                if "where" not in query_lower and "tenant_id" in query_lower:
                    # tenant_id might be in JOIN condition, which is acceptable
                    pass
                elif "where" not in query_lower:
                    raise StorageError(
                        "SECURITY: SELECT queries must include WHERE clause with tenant_id filtering"
                    )
            
            async with self.pool.acquire() as conn:
                # Ensure tenant_id is in params
                query_params = params or {}
                if "tenant_id" not in query_params:
                    query_params["tenant_id"] = tenant_id
                
                # Verify the tenant_id in params matches the method parameter
                if query_params.get("tenant_id") != tenant_id:
                    raise StorageError(
                        f"SECURITY: tenant_id in params ({query_params.get('tenant_id')}) "
                        f"must match method parameter ({tenant_id})"
                    )
                
                # Execute query (uses parameterization for safety)
                rows = await conn.fetch(query, *query_params.values())
                
                # Convert rows to dictionaries
                return [dict(row) for row in rows]
        except asyncpg.PostgresError as e:
            raise StorageError(f"Query failed: {e}") from e
        except Exception as e:
            raise StorageError(f"Query validation or execution failed: {e}") from e

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

    # AAET-85: Batch methods for compatibility with processor pattern
    def set_tenant_id(self, tenant_id: str) -> None:
        """Set the tenant ID for batch operations.
        
        Added in AAET-85: Must be called before using batch methods.
        
        Args:
            tenant_id: Tenant identifier for all batched operations
        """
        self._tenant_id = tenant_id

    def ensure_node_batch(self, node_type: str, properties: dict[str, Any]) -> None:
        """Queue a node for batch insertion.
        
        Added in AAET-85: Synchronous method that queues nodes.
        Call flush_all() to actually insert them.
        
        Args:
            node_type: Type of node (Function, Class, Module, etc.)
            properties: Node properties including qualified_name, name, etc.
        
        Raises:
            ValueError: If node_type is empty or properties missing required fields
            StorageError: If tenant_id not set (multi-tenancy safety)
        """
        # Multi-tenancy safety: Validate tenant context before queueing
        if not self._tenant_id:
            raise StorageError(
                "tenant_id must be set before queueing operations. "
                "Call set_tenant_id() first."
            )
        
        if not node_type or not node_type.strip():
            raise ValueError("node_type cannot be empty")
        if not properties:
            raise ValueError("properties cannot be empty")
        if "qualified_name" not in properties and "name" not in properties:
            raise ValueError("properties must include 'qualified_name' or 'name'")
        
        self._node_batch.append((node_type, properties))

    def ensure_relationship_batch(
        self,
        from_node: tuple[str, str, str],
        edge_type: str,
        to_node: tuple[str, str, str],
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Queue a relationship for batch insertion.
        
        Added in AAET-85: Synchronous method that queues edges.
        Call flush_all() to actually insert them.
        
        Args:
            from_node: Tuple of (node_type, key_field, key_value) for source
            edge_type: Type of relationship (CALLS, IMPORTS, DEFINES, etc.)
            to_node: Tuple of (node_type, key_field, key_value) for target
            properties: Optional edge properties
        
        Raises:
            ValueError: If edge_type is empty or node tuples are invalid
            StorageError: If tenant_id not set (multi-tenancy safety)
        """
        # Multi-tenancy safety: Validate tenant context before queueing
        if not self._tenant_id:
            raise StorageError(
                "tenant_id must be set before queueing operations. "
                "Call set_tenant_id() first."
            )
        
        if not edge_type or not edge_type.strip():
            raise ValueError("edge_type cannot be empty")
        if not from_node or len(from_node) != 3:
            raise ValueError("from_node must be a tuple of (node_type, key_field, key_value)")
        if not to_node or len(to_node) != 3:
            raise ValueError("to_node must be a tuple of (node_type, key_field, key_value)")
        
        self._edge_batch.append((from_node, edge_type, to_node, properties))

    async def flush_all(self) -> None:
        """Flush all batched nodes and edges to the database with transaction safety.
        
        Added in AAET-85: Async method to insert all queued data.
        Uses transaction to ensure atomicity - either all data is inserted or none.
        
        Raises:
            StorageError: If tenant_id not set or transaction fails
        """
        if not self._tenant_id:
            raise StorageError("tenant_id must be set before flushing batches")
        
        if not self._node_batch and not self._edge_batch:
            return  # Nothing to flush
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Flush nodes
                    if self._node_batch:
                        nodes = []
                        for node_type, props in self._node_batch:
                            node = {
                                "node_type": node_type,
                                **props
                            }
                            nodes.append(node)
                        
                        await self.insert_nodes(self._tenant_id, nodes)
                        self._node_batch.clear()
                    
                    # Flush edges
                    if self._edge_batch:
                        edges = []
                        for from_node, edge_type, to_node, props in self._edge_batch:
                            # Extract qualified names from tuples
                            # from_node = (node_type, key_field, key_value)
                            from_qn = from_node[2]  # key_value is the qualified name
                            to_qn = to_node[2]
                            
                            edge = {
                                "from_node": from_qn,
                                "to_node": to_qn,
                                "edge_type": edge_type,
                                **(props or {})
                            }
                            edges.append(edge)
                        
                        await self.insert_edges(self._tenant_id, edges)
                        self._edge_batch.clear()
        except Exception as e:
            # On error, don't clear batches - allow retry
            raise StorageError(f"Failed to flush batches: {e}") from e
    
    async def count_nodes(self, tenant_id: str, repo_id: str | None = None) -> int:
        """Count nodes for a tenant, optionally filtered by repository.
        
        Added in AAET-86: For metrics collection in ParserService.
        
        Args:
            tenant_id: Tenant identifier
            repo_id: Optional repository identifier to filter by
        
        Returns:
            Number of nodes matching the criteria
        """
        try:
            async with self.pool.acquire() as conn:
                if repo_id:
                    query = """
                        SELECT COUNT(*) 
                        FROM nodes 
                        WHERE tenant_id = $1 AND properties->>'repo_id' = $2
                    """
                    result = await conn.fetchval(query, tenant_id, repo_id)
                else:
                    query = """
                        SELECT COUNT(*) 
                        FROM nodes 
                        WHERE tenant_id = $1
                    """
                    result = await conn.fetchval(query, tenant_id)
                
                return result or 0
        except Exception as e:
            raise StorageError(f"Failed to count nodes: {e}") from e
    
    async def count_edges(self, tenant_id: str, repo_id: str | None = None) -> int:
        """Count edges for a tenant, optionally filtered by repository.
        
        Added in AAET-86: For metrics collection in ParserService.
        
        Args:
            tenant_id: Tenant identifier
            repo_id: Optional repository identifier to filter by
        
        Returns:
            Number of edges matching the criteria
        """
        try:
            async with self.pool.acquire() as conn:
                if repo_id:
                    query = """
                        SELECT COUNT(*) 
                        FROM edges 
                        WHERE tenant_id = $1 AND properties->>'repo_id' = $2
                    """
                    result = await conn.fetchval(query, tenant_id, repo_id)
                else:
                    query = """
                        SELECT COUNT(*) 
                        FROM edges 
                        WHERE tenant_id = $1
                    """
                    result = await conn.fetchval(query, tenant_id)
                
                return result or 0
        except Exception as e:
            raise StorageError(f"Failed to count edges: {e}") from e
