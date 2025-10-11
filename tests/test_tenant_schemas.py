"""Test tenant context schemas (AAET-83)."""

import pytest
from uuid import UUID, uuid4

from libs.code_graph_rag.schemas import (
    ParsedNode,
    ParsedEdge,
    ParsedFile,
    NodeType,
    EdgeType,
)


def test_parsed_node_with_tenant_context():
    """Test ParsedNode includes tenant_id and repo_id."""
    tenant_id = str(uuid4())
    repo_id = str(uuid4())
    
    node = ParsedNode(
        tenant_id=tenant_id,
        repo_id=repo_id,
        node_type=NodeType.FUNCTION,
        name="test_function",
        qualified_name="module.test_function",
        file_path="test.py",
        start_line=1,
        end_line=10,
    )
    
    assert node.tenant_id == tenant_id
    assert node.repo_id == repo_id
    assert node.node_type == NodeType.FUNCTION
    assert node.name == "test_function"


def test_parsed_node_with_string_ids():
    """Test ParsedNode accepts string IDs (for flexibility)."""
    node = ParsedNode(
        tenant_id="tenant-123",
        repo_id="repo-456",
        node_type=NodeType.CLASS,
        name="TestClass",
        qualified_name="module.TestClass",
        file_path="test.py",
    )
    
    assert node.tenant_id == "tenant-123"
    assert node.repo_id == "repo-456"


def test_parsed_edge_with_tenant_context():
    """Test ParsedEdge includes tenant_id and repo_id."""
    tenant_id = str(uuid4())
    repo_id = str(uuid4())
    
    edge = ParsedEdge(
        tenant_id=tenant_id,
        repo_id=repo_id,
        from_node="module.main",
        to_node="module.helper",
        edge_type=EdgeType.CALLS,
    )
    
    assert edge.tenant_id == tenant_id
    assert edge.repo_id == repo_id
    assert edge.from_node == "module.main"
    assert edge.to_node == "module.helper"
    assert edge.edge_type == EdgeType.CALLS


def test_parsed_file_complete():
    """Test ParsedFile with nodes and edges."""
    tenant_id = str(uuid4())
    repo_id = str(uuid4())
    
    parsed_file = ParsedFile(
        tenant_id=tenant_id,
        repo_id=repo_id,
        file_path="test.py",
        language="python",
        nodes=[
            ParsedNode(
                tenant_id=tenant_id,
                repo_id=repo_id,
                node_type=NodeType.FUNCTION,
                name="main",
                qualified_name="module.main",
                file_path="test.py",
                start_line=1,
                end_line=5,
            ),
            ParsedNode(
                tenant_id=tenant_id,
                repo_id=repo_id,
                node_type=NodeType.FUNCTION,
                name="helper",
                qualified_name="module.helper",
                file_path="test.py",
                start_line=7,
                end_line=10,
            ),
        ],
        edges=[
            ParsedEdge(
                tenant_id=tenant_id,
                repo_id=repo_id,
                from_node="module.main",
                to_node="module.helper",
                edge_type=EdgeType.CALLS,
            )
        ],
    )
    
    assert parsed_file.tenant_id == tenant_id
    assert parsed_file.repo_id == repo_id
    assert len(parsed_file.nodes) == 2
    assert len(parsed_file.edges) == 1
    assert parsed_file.language == "python"


def test_node_types_enum():
    """Test NodeType enum values."""
    assert NodeType.FUNCTION == "Function"
    assert NodeType.CLASS == "Class"
    assert NodeType.METHOD == "Method"
    assert NodeType.MODULE == "Module"


def test_edge_types_enum():
    """Test EdgeType enum values."""
    assert EdgeType.CALLS == "CALLS"
    assert EdgeType.IMPORTS == "IMPORTS"
    assert EdgeType.DEFINES == "DEFINES"
    assert EdgeType.INHERITS == "INHERITS"


def test_tenant_isolation():
    """Test that different tenants have different IDs."""
    tenant1_id = str(uuid4())
    tenant2_id = str(uuid4())
    
    node1 = ParsedNode(
        tenant_id=tenant1_id,
        repo_id=str(uuid4()),
        node_type=NodeType.FUNCTION,
        name="func",
        qualified_name="module.func",
        file_path="test.py",
    )
    
    node2 = ParsedNode(
        tenant_id=tenant2_id,
        repo_id=str(uuid4()),
        node_type=NodeType.FUNCTION,
        name="func",
        qualified_name="module.func",
        file_path="test.py",
    )
    
    # Same function name but different tenants
    assert node1.tenant_id != node2.tenant_id
    assert node1.name == node2.name
    assert node1.qualified_name == node2.qualified_name


def test_empty_tenant_id_rejected():
    """Test that empty tenant_id is rejected."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError, match="tenant_id and repo_id cannot be empty"):
        ParsedNode(
            tenant_id="",  # Empty string should be rejected
            repo_id=str(uuid4()),
            node_type=NodeType.FUNCTION,
            name="func",
            qualified_name="module.func",
            file_path="test.py",
        )


def test_empty_repo_id_rejected():
    """Test that empty repo_id is rejected."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError, match="tenant_id and repo_id cannot be empty"):
        ParsedNode(
            tenant_id=str(uuid4()),
            repo_id="   ",  # Whitespace-only string should be rejected
            node_type=NodeType.FUNCTION,
            name="func",
            qualified_name="module.func",
            file_path="test.py",
        )


def test_edge_has_repo_id():
    """Test that ParsedEdge includes repo_id."""
    tenant_id = str(uuid4())
    repo_id = str(uuid4())
    
    edge = ParsedEdge(
        tenant_id=tenant_id,
        repo_id=repo_id,
        from_node="module.main",
        to_node="module.helper",
        edge_type=EdgeType.CALLS,
    )
    
    assert edge.tenant_id == tenant_id
    assert edge.repo_id == repo_id


def test_extra_fields_rejected():
    """Test that extra fields are rejected (strict validation)."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        ParsedNode(
            tenant_id=str(uuid4()),
            repo_id=str(uuid4()),
            node_type=NodeType.FUNCTION,
            name="func",
            qualified_name="module.func",
            file_path="test.py",
            extra_field="should_fail",  # Extra field should be rejected
        )


def test_invalid_uuid_format_rejected():
    """Test that invalid UUID format is rejected."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError, match="Invalid UUID format"):
        ParsedNode(
            tenant_id="not-a-valid-uuid",
            repo_id=str(uuid4()),
            node_type=NodeType.FUNCTION,
            name="func",
            qualified_name="module.func",
            file_path="test.py",
        )


def test_valid_uuid_string_accepted():
    """Test that valid UUID strings are accepted."""
    tenant_id = str(uuid4())
    repo_id = str(uuid4())
    
    node = ParsedNode(
        tenant_id=tenant_id,
        repo_id=repo_id,
        node_type=NodeType.FUNCTION,
        name="func",
        qualified_name="module.func",
        file_path="test.py",
    )
    
    assert node.tenant_id == tenant_id
    assert node.repo_id == repo_id
    assert isinstance(node.tenant_id, str)
    assert isinstance(node.repo_id, str)
