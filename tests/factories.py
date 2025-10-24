"""Test data factories using factory-boy.

This module provides factories for generating test data for:
- Tenants
- Users
- Repositories
- Code nodes
- Code edges
- Embeddings
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import factory
from factory import Faker, LazyAttribute, SubFactory
from factory.alchemy import SQLAlchemyModelFactory

from app.config import settings
from app.models.code_graph import CodeEdge, CodeNode, Embedding
from app.models.repository import Repository
from app.models.tenant import Tenant, User


# ============================================================================
# Base Factory
# ============================================================================

class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configuration."""
    
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


# ============================================================================
# Tenant & User Factories
# ============================================================================

class TenantFactory(BaseFactory):
    """Factory for creating test tenants."""
    
    class Meta:
        model = Tenant
    
    id = LazyAttribute(lambda _: uuid4())
    name = Faker("company")
    slug = LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    settings = factory.Dict({
        "max_repositories": 10,
        "max_users": 5,
        "features": ["code_search", "embeddings"],
    })
    is_active = True
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class UserFactory(BaseFactory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
    
    id = LazyAttribute(lambda _: uuid4())
    tenant_id = LazyAttribute(lambda _: uuid4())
    email = Faker("email")
    username = Faker("user_name")
    full_name = Faker("name")
    hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNqN8RLUW"  # "password"
    is_active = True
    is_superuser = False
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    
    # Create with tenant relationship
    tenant = SubFactory(TenantFactory)


# ============================================================================
# Repository Factory
# ============================================================================

class RepositoryFactory(BaseFactory):
    """Factory for creating test repositories."""
    
    class Meta:
        model = Repository
    
    id = LazyAttribute(lambda _: uuid4())
    tenant_id = LazyAttribute(lambda _: uuid4())
    name = Faker("slug")
    url = LazyAttribute(lambda obj: f"https://github.com/test/{obj.name}")
    branch = "main"
    language = factory.Iterator(["python", "javascript", "typescript", "java", "go"])
    status = "active"
    last_indexed_at = None
    metadata = factory.Dict({
        "stars": Faker("random_int", min=0, max=10000),
        "forks": Faker("random_int", min=0, max=1000),
    })
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    
    # Create with tenant relationship
    tenant = SubFactory(TenantFactory)


# ============================================================================
# Code Graph Factories
# ============================================================================

class CodeNodeFactory(BaseFactory):
    """Factory for creating test code nodes."""
    
    class Meta:
        model = CodeNode
    
    id = LazyAttribute(lambda _: uuid4())
    tenant_id = LazyAttribute(lambda _: uuid4())
    repository_id = LazyAttribute(lambda _: uuid4())
    node_type = factory.Iterator(["function", "class", "module", "variable"])
    name = Faker("word")
    qualified_name = LazyAttribute(lambda obj: f"module.{obj.name}")
    file_path = LazyAttribute(lambda obj: f"src/{obj.name}.py")
    start_line = Faker("random_int", min=1, max=100)
    end_line = LazyAttribute(lambda obj: obj.start_line + Faker("random_int", min=1, max=50).evaluate(None, None, {"locale": None}))
    code_snippet = LazyAttribute(lambda obj: f"def {obj.name}():\n    pass")
    docstring = Faker("sentence")
    language = "python"
    metadata = factory.Dict({
        "complexity": Faker("random_int", min=1, max=10),
        "parameters": [],
    })
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class CodeEdgeFactory(BaseFactory):
    """Factory for creating test code edges."""
    
    class Meta:
        model = CodeEdge
    
    id = LazyAttribute(lambda _: uuid4())
    tenant_id = LazyAttribute(lambda _: uuid4())
    repository_id = LazyAttribute(lambda _: uuid4())
    source_node_id = LazyAttribute(lambda _: uuid4())
    target_node_id = LazyAttribute(lambda _: uuid4())
    edge_type = factory.Iterator(["calls", "imports", "inherits", "uses"])
    metadata = factory.Dict({
        "weight": Faker("random_int", min=1, max=10),
    })
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class EmbeddingFactory(BaseFactory):
    """Factory for creating test embeddings."""
    
    class Meta:
        model = Embedding
    
    id = LazyAttribute(lambda _: uuid4())
    tenant_id = LazyAttribute(lambda _: uuid4())
    node_id = LazyAttribute(lambda _: uuid4())
    model_name = LazyAttribute(lambda _: settings.voyage_model_name)
    embedding_vector = LazyAttribute(lambda _: [0.1] * settings.voyage_embedding_dimension)
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


# ============================================================================
# Convenience Functions
# ============================================================================

def create_tenant(**kwargs) -> Tenant:
    """Create a test tenant with optional overrides."""
    return TenantFactory.create(**kwargs)


def create_user(tenant: Tenant | None = None, **kwargs: Any) -> User:
    """
    Create a test user with optional tenant and overrides.
    
    Args:
        tenant: Tenant object to associate with user
        **kwargs: Additional overrides for user creation
        
    Returns:
        Created User instance
        
    Raises:
        ValueError: If neither tenant nor tenant_id is provided
    """
    if tenant:
        kwargs["tenant"] = tenant
        kwargs["tenant_id"] = tenant.id
    elif "tenant_id" not in kwargs:
        # Auto-create tenant if not provided
        tenant = create_tenant()
        kwargs["tenant"] = tenant
        kwargs["tenant_id"] = tenant.id
    return UserFactory.create(**kwargs)


def create_repository(tenant: Tenant | None = None, **kwargs: Any) -> Repository:
    """
    Create a test repository with optional tenant and overrides.
    
    Args:
        tenant: Tenant object to associate with repository
        **kwargs: Additional overrides for repository creation
        
    Returns:
        Created Repository instance
        
    Raises:
        ValueError: If neither tenant nor tenant_id is provided
    """
    if tenant:
        kwargs["tenant"] = tenant
        kwargs["tenant_id"] = tenant.id
    elif "tenant_id" not in kwargs:
        # Auto-create tenant if not provided
        tenant = create_tenant()
        kwargs["tenant"] = tenant
        kwargs["tenant_id"] = tenant.id
    return RepositoryFactory.create(**kwargs)


def create_code_node(
    tenant: Tenant | None = None,
    repository: Repository | None = None,
    **kwargs
) -> CodeNode:
    """Create a test code node with optional tenant/repository and overrides."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    if repository:
        kwargs["repository_id"] = repository.id
    return CodeNodeFactory.create(**kwargs)


def create_code_edge(
    tenant: Tenant | None = None,
    repository: Repository | None = None,
    source_node: CodeNode | None = None,
    target_node: CodeNode | None = None,
    **kwargs
) -> CodeEdge:
    """Create a test code edge with optional relationships and overrides."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    if repository:
        kwargs["repository_id"] = repository.id
    if source_node:
        kwargs["source_node_id"] = source_node.id
    if target_node:
        kwargs["target_node_id"] = target_node.id
    return CodeEdgeFactory.create(**kwargs)


def create_embedding(
    tenant: Tenant | None = None,
    node: CodeNode | None = None,
    **kwargs
) -> Embedding:
    """Create a test embedding with optional relationships and overrides."""
    if tenant:
        kwargs["tenant_id"] = tenant.id
    if node:
        kwargs["node_id"] = node.id
    return EmbeddingFactory.create(**kwargs)


# ============================================================================
# Batch Creation Helpers
# ============================================================================

def create_tenant_with_users(
    user_count: int = 3,
    **tenant_kwargs: Any
) -> tuple[Tenant, list[User]]:
    """Create a tenant with multiple users."""
    tenant = create_tenant(**tenant_kwargs)
    users = [create_user(tenant=tenant) for _ in range(user_count)]
    return tenant, users


def create_repository_with_nodes(
    node_count: int = 10,
    tenant: Tenant | None = None,
    **repo_kwargs: Any
) -> tuple[Repository, list[CodeNode]]:
    """Create a repository with multiple code nodes."""
    if not tenant:
        tenant = create_tenant()
    
    repository = create_repository(tenant=tenant, **repo_kwargs)
    nodes = [
        create_code_node(tenant=tenant, repository=repository)
        for _ in range(node_count)
    ]
    return repository, nodes


def create_complete_code_graph(
    node_count: int = 10,
    edge_count: int = 15,
    tenant: Tenant | None = None,
) -> tuple[Repository, list[CodeNode], list[CodeEdge]]:
    """Create a complete code graph with nodes and edges."""
    repository, nodes = create_repository_with_nodes(node_count, tenant)
    
    edges: list[CodeEdge] = []
    for _ in range(edge_count):
        source = factory.random.randgen.choice(nodes)
        target = factory.random.randgen.choice(nodes)
        if source.id != target.id:  # Avoid self-loops
            edge = create_code_edge(
                tenant=repository.tenant,
                repository=repository,
                source_node=source,
                target_node=target,
            )
            edges.append(edge)
    
    return repository, nodes, edges
