"""Test tenant context in GraphUpdater (AAET-83)."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from libs.code_graph_rag.graph_builder import GraphUpdater


def test_graph_updater_requires_tenant_id():
    """Test that GraphUpdater requires tenant_id."""
    with pytest.raises(ValueError, match="tenant_id is required"):
        GraphUpdater(
            tenant_id="",  # Empty tenant_id should fail
            repo_id="repo-123",
            ingestor=Mock(),
            repo_path=Path("/tmp/test"),
            parsers={},
            queries={},
        )


def test_graph_updater_requires_repo_id():
    """Test that GraphUpdater requires repo_id."""
    with pytest.raises(ValueError, match="repo_id is required"):
        GraphUpdater(
            tenant_id="tenant-123",
            repo_id="   ",  # Whitespace-only repo_id should fail
            ingestor=Mock(),
            repo_path=Path("/tmp/test"),
            parsers={},
            queries={},
        )


def test_graph_updater_accepts_valid_tenant_context():
    """Test that GraphUpdater accepts valid tenant_id and repo_id."""
    updater = GraphUpdater(
        tenant_id="tenant-123",
        repo_id="repo-456",
        ingestor=Mock(),
        repo_path=Path("/tmp/test"),
        parsers={},
        queries={},
    )
    
    assert updater.tenant_id == "tenant-123"
    assert updater.repo_id == "repo-456"


def test_graph_updater_tenant_context_passed_to_factory():
    """Test that tenant context is passed to ProcessorFactory."""
    updater = GraphUpdater(
        tenant_id="tenant-123",
        repo_id="repo-456",
        ingestor=Mock(),
        repo_path=Path("/tmp/test"),
        parsers={},
        queries={},
    )
    
    # Verify factory has tenant context
    assert updater.factory.tenant_id == "tenant-123"
    assert updater.factory.repo_id == "repo-456"
