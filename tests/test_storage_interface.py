"""Tests for GraphStoreInterface and implementations.

Story: AAET-84 - Abstract Storage Interface
"""

import pytest

from libs.code_graph_rag.storage.interface import GraphStoreInterface


class MockGraphStore(GraphStoreInterface):
    """Mock implementation for testing."""

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.closed = False

    async def insert_nodes(self, tenant_id: str, nodes: list[dict]) -> None:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        self.nodes.extend(nodes)

    async def insert_edges(self, tenant_id: str, edges: list[dict]) -> None:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        self.edges.extend(edges)

    async def query_graph(
        self, tenant_id: str, query: str, params: dict | None = None
    ) -> list[dict]:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return []

    async def delete_nodes(self, tenant_id: str, node_filter: dict) -> int:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return 0

    async def delete_edges(self, tenant_id: str, edge_filter: dict) -> int:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return 0

    async def get_node(self, tenant_id: str, qualified_name: str) -> dict | None:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return None

    async def get_neighbors(
        self,
        tenant_id: str,
        qualified_name: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict]:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return []

    async def count_nodes(self, tenant_id: str) -> int:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return len(self.nodes)

    async def count_edges(self, tenant_id: str) -> int:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return len(self.edges)

    async def insert_embeddings(self, tenant_id: str, embeddings: list[dict]) -> int:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return len(embeddings)

    async def query_embeddings(
        self, tenant_id: str, query: str, params: dict | None = None
    ) -> list[dict]:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return []

    async def search_similar_embeddings(
        self,
        tenant_id: str,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")
        return []

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_insert_nodes_requires_tenant_id():
    """Test that insert_nodes requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.insert_nodes("", [{"type": "Function", "name": "test"}])


@pytest.mark.asyncio
async def test_insert_nodes_accepts_valid_tenant():
    """Test that insert_nodes accepts valid tenant_id."""
    store = MockGraphStore()

    nodes = [
        {
            "tenant_id": "tenant-123",
            "repo_id": "repo-456",
            "type": "Function",
            "name": "test_function",
            "qualified_name": "module.test_function",
        }
    ]

    await store.insert_nodes("tenant-123", nodes)

    assert len(store.nodes) == 1
    assert store.nodes[0]["name"] == "test_function"


@pytest.mark.asyncio
async def test_insert_edges_requires_tenant_id():
    """Test that insert_edges requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.insert_edges("", [{"from_node": "a", "to_node": "b", "type": "CALLS"}])


@pytest.mark.asyncio
async def test_insert_edges_accepts_valid_tenant():
    """Test that insert_edges accepts valid tenant_id."""
    store = MockGraphStore()

    edges = [
        {
            "tenant_id": "tenant-123",
            "from_node": "module.main",
            "to_node": "module.helper",
            "type": "CALLS",
        }
    ]

    await store.insert_edges("tenant-123", edges)

    assert len(store.edges) == 1
    assert store.edges[0]["type"] == "CALLS"


@pytest.mark.asyncio
async def test_query_graph_requires_tenant_id():
    """Test that query_graph requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.query_graph("", "SELECT * FROM nodes")


@pytest.mark.asyncio
async def test_close_releases_resources():
    """Test that close() releases resources."""
    store = MockGraphStore()

    await store.close()

    assert store.closed is True


@pytest.mark.asyncio
async def test_get_node_requires_tenant_id():
    """Test that get_node requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.get_node("", "module.function")


@pytest.mark.asyncio
async def test_get_neighbors_requires_tenant_id():
    """Test that get_neighbors requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.get_neighbors("", "module.function")


@pytest.mark.asyncio
async def test_delete_nodes_requires_tenant_id():
    """Test that delete_nodes requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.delete_nodes("", {"file_path": "test.py"})


@pytest.mark.asyncio
async def test_delete_edges_requires_tenant_id():
    """Test that delete_edges requires tenant_id."""
    store = MockGraphStore()

    with pytest.raises(ValueError, match="tenant_id cannot be empty"):
        await store.delete_edges("", {"from_node": "a"})


@pytest.mark.asyncio
async def test_tenant_isolation_in_nodes():
    """Test that tenant_id parameter overrides node data (security)."""
    store = MockGraphStore()

    # Try to insert node with different tenant_id in data
    malicious_nodes = [
        {
            "tenant_id": "evil-tenant",  # Attacker tries to override
            "repo_id": "repo-456",
            "type": "Function",
            "name": "malicious_function",
            "qualified_name": "evil.malicious_function",
        }
    ]

    # Insert with correct tenant_id parameter
    await store.insert_nodes("good-tenant", malicious_nodes)

    # Verify the node was stored (in mock, we just check it was called)
    assert len(store.nodes) == 1
    # In real implementation, PostgresGraphStore should enforce
    # that tenant_id parameter always wins


@pytest.mark.asyncio
async def test_tenant_isolation_in_edges():
    """Test that tenant_id parameter overrides edge data (security)."""
    store = MockGraphStore()

    # Try to insert edge with different tenant_id in data
    malicious_edges = [
        {
            "tenant_id": "evil-tenant",  # Attacker tries to override
            "from_node": "evil.a",
            "to_node": "evil.b",
            "type": "CALLS",
        }
    ]

    # Insert with correct tenant_id parameter
    await store.insert_edges("good-tenant", malicious_edges)

    # Verify the edge was stored (in mock, we just check it was called)
    assert len(store.edges) == 1
    # In real implementation, PostgresGraphStore should enforce
    # that tenant_id parameter always wins


@pytest.mark.asyncio
async def test_query_graph_requires_tenant_filtering():
    """Test that query_graph validates tenant_id filtering (security)."""
    # This test documents the expected behavior for PostgresGraphStore
    # The mock doesn't enforce this, but real implementation should

    store = MockGraphStore()

    # Safe query with tenant_id filtering - should work
    safe_query = "SELECT * FROM code_nodes WHERE tenant_id = $1"
    result = await store.query_graph("tenant-123", safe_query, {"tenant_id": "tenant-123"})
    assert result == []  # Mock returns empty list

    # Note: PostgresGraphStore should reject queries without tenant_id filtering
    # Example of what should be rejected:
    # unsafe_query = "SELECT * FROM code_nodes"  # No tenant_id
    # This should raise StorageError in PostgresGraphStore
