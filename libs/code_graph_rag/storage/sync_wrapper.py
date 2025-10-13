"""Synchronous wrapper for async GraphStoreInterface implementations.

This module provides a synchronous wrapper that allows async storage backends
to be used in synchronous code (like the current GraphUpdater).

This is a temporary bridge until AAET-85 converts GraphUpdater to async.

Added in AAET-84: Sync wrapper for async storage backends.
"""

import asyncio
from typing import Any

from .interface import GraphStoreInterface, StorageError


class SyncGraphStoreWrapper:
    """Synchronous wrapper for async GraphStoreInterface implementations.
    
    This wrapper allows async storage backends (like PostgresGraphStore) to be
    used in synchronous code by running async operations in an event loop.
    
    ⚠️ WARNING: This is a temporary solution until GraphUpdater is converted
    to async in AAET-85. Using this wrapper has performance implications as
    it creates/manages event loops for each operation.
    
    Example:
        # Wrap async PostgresGraphStore for sync usage
        async_store = PostgresGraphStore("postgresql://...")
        await async_store.connect()
        
        sync_store = SyncGraphStoreWrapper(async_store)
        
        # Now can be used synchronously
        sync_store.insert_nodes("tenant-123", nodes)
    """
    
    def __init__(self, async_store: GraphStoreInterface):
        """Initialize sync wrapper.
        
        Args:
            async_store: Async GraphStoreInterface implementation
        """
        self.async_store = async_store
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop for running async operations."""
        if self._loop is None or self._loop.is_closed():
            try:
                # Try to get existing loop
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create new loop if none exists
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        loop = self._get_or_create_loop()
        try:
            return loop.run_until_complete(coro)
        except Exception as e:
            raise StorageError(f"Async operation failed: {e}") from e
    
    def insert_nodes(
        self,
        tenant_id: str,
        nodes: list[dict[str, Any]],
    ) -> None:
        """Insert nodes synchronously."""
        self._run_async(self.async_store.insert_nodes(tenant_id, nodes))
    
    def insert_edges(
        self,
        tenant_id: str,
        edges: list[dict[str, Any]],
    ) -> None:
        """Insert edges synchronously."""
        self._run_async(self.async_store.insert_edges(tenant_id, edges))
    
    def query_graph(
        self,
        tenant_id: str,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute query synchronously."""
        return self._run_async(self.async_store.query_graph(tenant_id, query, params))
    
    def delete_nodes(
        self,
        tenant_id: str,
        node_filter: dict[str, Any],
    ) -> int:
        """Delete nodes synchronously."""
        return self._run_async(self.async_store.delete_nodes(tenant_id, node_filter))
    
    def delete_edges(
        self,
        tenant_id: str,
        edge_filter: dict[str, Any],
    ) -> int:
        """Delete edges synchronously."""
        return self._run_async(self.async_store.delete_edges(tenant_id, edge_filter))
    
    def get_node(
        self,
        tenant_id: str,
        qualified_name: str,
    ) -> dict[str, Any] | None:
        """Get node synchronously."""
        return self._run_async(self.async_store.get_node(tenant_id, qualified_name))
    
    def get_neighbors(
        self,
        tenant_id: str,
        qualified_name: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """Get neighbors synchronously."""
        return self._run_async(
            self.async_store.get_neighbors(tenant_id, qualified_name, edge_type, direction)
        )
    
    def close(self) -> None:
        """Close store synchronously."""
        self._run_async(self.async_store.close())
        if self._loop and not self._loop.is_closed():
            self._loop.close()
