"""Example tests demonstrating fixture usage.

This module shows how to use the test fixtures and factories
for writing effective tests.
"""

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant, User
from app.models.repository import Repository


# ============================================================================
# Unit Tests (Fast, No External Dependencies)
# ============================================================================

@pytest.mark.unit
def test_sample_data_fixtures(sample_tenant_data, sample_user_data):
    """Test that sample data fixtures work."""
    assert sample_tenant_data["name"] == "Test Tenant"
    assert sample_user_data["email"] == "test@example.com"


@pytest.mark.unit
def test_benchmark_timer(benchmark_timer):
    """Test the benchmark timer fixture."""
    with benchmark_timer() as timer:
        # Simulate some work
        sum([i for i in range(1000)])
    
    # Timer should have recorded elapsed time
    assert timer.elapsed > 0
    assert timer.elapsed < 1.0  # Should be very fast


# ============================================================================
# Integration Tests (Require Database)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_session(db_session):
    """Test that database session fixture works."""
    # Session should be available
    assert db_session is not None
    
    # Should be able to execute queries
    result = await db_session.execute(select(Tenant))
    tenants = result.scalars().all()
    
    # Should start with empty database
    assert len(tenants) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_create_tenant(db_session, factories):
    """Test creating a tenant using factories."""
    # Create tenant using factory
    tenant = factories.create_tenant(name="Test Company")
    
    # Tenant should be created
    assert tenant.id is not None
    assert tenant.name == "Test Company"
    assert tenant.is_active is True
    
    # Should be in database
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == tenant.id)
    )
    db_tenant = result.scalar_one_or_none()
    assert db_tenant is not None
    assert db_tenant.name == "Test Company"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_create_user_with_tenant(db_session, factories):
    """Test creating a user with tenant relationship."""
    # Create tenant first
    tenant = factories.create_tenant()
    
    # Create user for that tenant
    user = factories.create_user(tenant=tenant)
    
    # User should be linked to tenant
    assert user.tenant_id == tenant.id
    assert user.tenant.id == tenant.id
    
    # Should be in database
    result = await db_session.execute(
        select(User).where(User.id == user.id)
    )
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.tenant_id == tenant.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_batch_creation(db_session, factories):
    """Test creating multiple entities with batch helpers."""
    # Create tenant with multiple users
    tenant, users = factories.create_tenant_with_users(user_count=5)
    
    # Should have created 5 users
    assert len(users) == 5
    
    # All users should belong to same tenant
    for user in users:
        assert user.tenant_id == tenant.id
    
    # Should be in database
    result = await db_session.execute(
        select(User).where(User.tenant_id == tenant.id)
    )
    db_users = result.scalars().all()
    assert len(db_users) == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_repository_with_nodes(db_session, factories):
    """Test creating repository with code nodes."""
    # Create repository with nodes
    repository, nodes = factories.create_repository_with_nodes(node_count=10)
    
    # Should have created 10 nodes
    assert len(nodes) == 10
    
    # All nodes should belong to same repository
    for node in nodes:
        assert node.repository_id == repository.id
        assert node.tenant_id == repository.tenant_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_complete_code_graph(db_session, factories):
    """Test creating complete code graph with nodes and edges."""
    # Create complete graph
    repository, nodes, edges = factories.create_complete_code_graph(
        node_count=10,
        edge_count=15
    )
    
    # Should have created nodes and edges
    assert len(nodes) == 10
    assert len(edges) <= 15  # May be less due to duplicate prevention
    
    # All edges should connect nodes in the graph
    node_ids = {node.id for node in nodes}
    for edge in edges:
        assert edge.source_node_id in node_ids
        assert edge.target_node_id in node_ids


# ============================================================================
# Redis Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_client(redis_client):
    """Test Redis client fixture."""
    # Should be able to set and get values
    await redis_client.set("test_key", "test_value")
    value = await redis_client.get("test_key")
    
    assert value == "test_value"
    
    # Database should be flushed after test automatically


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_isolation(redis_client):
    """Test that Redis tests are isolated."""
    # This test should start with empty database
    keys = await redis_client.keys("*")
    assert len(keys) == 0


# ============================================================================
# API Tests
# ============================================================================

@pytest.mark.integration
def test_api_client(client):
    """Test FastAPI TestClient fixture."""
    # Should be able to make requests
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.integration
def test_api_with_database(client, factories):
    """Test API endpoints with database fixtures."""
    # Create test data
    tenant = factories.create_tenant()
    
    # Make API request (would need actual endpoint)
    # This is just an example structure
    response = client.get("/health")
    assert response.status_code == 200


# ============================================================================
# Slow Tests
# ============================================================================

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.asyncio
async def test_large_dataset_creation(db_session, factories):
    """Test creating large datasets (marked as slow)."""
    # Create large code graph
    repository, nodes, edges = factories.create_complete_code_graph(
        node_count=100,
        edge_count=500
    )
    
    # Should handle large datasets
    assert len(nodes) == 100
    assert len(edges) <= 500
