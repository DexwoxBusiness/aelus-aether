"""Test data factories for async SQLAlchemy.

This module provides async factory functions for generating test data for:
- Tenants
- Users
- Repositories
- Code nodes
- Code edges
- Embeddings

Note: We use async functions instead of factory-boy's SQLAlchemyModelFactory
because factory-boy doesn't support AsyncSession natively.
"""

import random
from datetime import datetime
from typing import Any
from uuid import uuid4

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_graph import CodeEdge, CodeEmbedding, CodeNode
from app.models.repository import Repository
from app.models.tenant import Tenant, User

# Initialize Faker instance
fake = Faker()


# ============================================================================
# Tenant & User Factories
# ============================================================================


async def create_tenant_async(session: AsyncSession, **kwargs: Any) -> Tenant:
    """Create a test tenant asynchronously."""
    defaults = {
        "id": uuid4(),
        "name": fake.company(),
        "api_key": f"test_api_key_{uuid4().hex}",
        "settings": {
            "max_repositories": 10,
            "max_users": 5,
            "features": ["code_search", "embeddings"],
        },
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    tenant = Tenant(**defaults)
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)
    return tenant


async def create_user_async(
    session: AsyncSession, tenant: Tenant | None = None, **kwargs: Any
) -> User:
    """Create a test user asynchronously."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    elif "tenant_id" not in kwargs:
        # Auto-create tenant if not provided
        tenant = await create_tenant_async(session)
        kwargs["tenant_id"] = tenant.id

    defaults = {
        "id": uuid4(),
        "email": fake.email(),
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNqN8RLUW",
        "role": "member",
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    user = User(**defaults)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


# ============================================================================
# Repository Factory
# ============================================================================


async def create_repository_async(
    session: AsyncSession, tenant: Tenant | None = None, **kwargs: Any
) -> Repository:
    """Create a test repository asynchronously."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    elif "tenant_id" not in kwargs:
        # Auto-create tenant if not provided
        tenant = await create_tenant_async(session)
        kwargs["tenant_id"] = tenant.id

    name = kwargs.get("name", fake.slug())
    defaults = {
        "id": uuid4(),
        "name": name,
        "git_url": f"https://github.com/test/{name}",
        "branch": "main",
        "language": random.choice(["python", "javascript", "typescript", "java", "go"]),
        "sync_status": "pending",
        "last_synced_at": None,
        "metadata_": {
            "stars": fake.random_int(min=0, max=10000),
            "forks": fake.random_int(min=0, max=1000),
        },
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    repository = Repository(**defaults)
    session.add(repository)
    await session.flush()
    await session.refresh(repository)
    return repository


# ============================================================================
# Code Graph Factories
# ============================================================================


async def create_code_node_async(
    session: AsyncSession,
    tenant: Tenant | None = None,
    repository: Repository | None = None,
    **kwargs: Any,
) -> CodeNode:
    """Create a test code node asynchronously."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    if repository:
        kwargs["repo_id"] = repository.id
        kwargs["tenant_id"] = repository.tenant_id

    name = kwargs.get("name", fake.word())
    start_line = kwargs.get("start_line", fake.random_int(min=1, max=100))
    defaults = {
        "id": uuid4(),
        "node_type": random.choice(["Function", "Class", "Module", "File"]),
        "name": name,
        "qualified_name": f"module.{name}",
        "file_path": f"src/{name}.py",
        "start_line": start_line,
        "end_line": start_line + fake.random_int(min=1, max=50),
        "source_code": f"def {name}():\n    pass",
        "docstring": fake.sentence(),
        "language": "python",
        "metadata_": {
            "complexity": fake.random_int(min=1, max=10),
            "parameters": [],
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    node = CodeNode(**defaults)
    session.add(node)
    await session.flush()
    await session.refresh(node)
    return node


async def create_code_edge_async(
    session: AsyncSession,
    tenant: Tenant | None = None,
    source_node: CodeNode | None = None,
    target_node: CodeNode | None = None,
    **kwargs: Any,
) -> CodeEdge:
    """Create a test code edge asynchronously."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    if source_node:
        kwargs["from_node_id"] = source_node.id
        kwargs["tenant_id"] = source_node.tenant_id
    if target_node:
        kwargs["to_node_id"] = target_node.id

    defaults = {
        "id": uuid4(),
        "edge_type": random.choice(["CALLS", "IMPORTS", "INHERITS", "USES_API"]),
        "metadata_": {
            "weight": fake.random_int(min=1, max=10),
        },
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    edge = CodeEdge(**defaults)
    session.add(edge)
    await session.flush()
    await session.refresh(edge)
    return edge


async def create_embedding_async(
    session: AsyncSession,
    tenant: Tenant | None = None,
    node: CodeNode | None = None,
    **kwargs: Any,
) -> CodeEmbedding:
    """Create a test embedding asynchronously."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    if node:
        kwargs["node_id"] = node.id
        kwargs["repo_id"] = node.repo_id
        kwargs["tenant_id"] = node.tenant_id

    defaults = {
        "id": uuid4(),
        "chunk_text": fake.text(),
        "chunk_index": 0,
        "embedding": [0.1] * 1536,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    embedding = CodeEmbedding(**defaults)
    session.add(embedding)
    await session.flush()
    await session.refresh(embedding)
    return embedding


# ============================================================================
# Convenience Aliases (for backward compatibility)
# ============================================================================

# These are kept for backward compatibility but should use the async versions
create_tenant = create_tenant_async
create_user = create_user_async
create_repository = create_repository_async
create_code_node = create_code_node_async
create_code_edge = create_code_edge_async
create_embedding = create_embedding_async


# ============================================================================
# Batch Creation Helpers
# ============================================================================


async def create_tenant_with_users(
    session: AsyncSession, user_count: int = 3, **tenant_kwargs: Any
) -> tuple[Tenant, list[User]]:
    """Create a tenant with multiple users asynchronously."""
    tenant = await create_tenant_async(session, **tenant_kwargs)
    users = [await create_user_async(session, tenant=tenant) for _ in range(user_count)]
    return tenant, users


async def create_repository_with_nodes(
    session: AsyncSession,
    node_count: int = 10,
    tenant: Tenant | None = None,
    **repo_kwargs: Any,
) -> tuple[Repository, list[CodeNode]]:
    """Create a repository with multiple code nodes asynchronously."""
    if not tenant:
        tenant = await create_tenant_async(session)

    repository = await create_repository_async(session, tenant=tenant, **repo_kwargs)
    nodes = [
        await create_code_node_async(session, tenant=tenant, repository=repository)
        for _ in range(node_count)
    ]
    return repository, nodes


async def create_complete_code_graph(
    session: AsyncSession,
    node_count: int = 10,
    edge_count: int = 15,
    tenant: Tenant | None = None,
) -> tuple[Repository, list[CodeNode], list[CodeEdge]]:
    """Create a complete code graph with nodes and edges asynchronously."""
    repository, nodes = await create_repository_with_nodes(session, node_count, tenant)

    edges: list[CodeEdge] = []
    for _ in range(edge_count):
        source = random.choice(nodes)
        target = random.choice(nodes)
        if source.id != target.id:  # Avoid self-loops
            edge = await create_code_edge_async(
                session,
                tenant=repository.tenant,
                source_node=source,
                target_node=target,
            )
            edges.append(edge)

    return repository, nodes, edges
