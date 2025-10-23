"""Initial schema: code_nodes, code_edges, embeddings tables

Revision ID: 001
Revises: 
Create Date: 2025-10-23

This migration creates the initial database schema for aelus-aether:
- code_nodes: Stores code entities (functions, classes, modules)
- code_edges: Stores relationships between code entities
- embeddings: Stores vector embeddings for semantic search

Implements AAET-8: Database Schema & Migrations Setup
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create code_nodes table
    op.create_table(
        'code_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('repo_id', sa.String(length=36), nullable=False),
        sa.Column('qualified_name', sa.Text(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'repo_id', 'qualified_name', name='unique_node_per_tenant')
    )
    
    # Create indexes for code_nodes
    op.create_index('idx_nodes_tenant_id', 'code_nodes', ['tenant_id'])
    op.create_index('idx_nodes_repo_id', 'code_nodes', ['repo_id'])
    op.create_index('idx_nodes_qualified_name', 'code_nodes', ['qualified_name'])
    op.create_index('idx_nodes_node_type', 'code_nodes', ['node_type'])
    op.create_index('idx_nodes_file_path', 'code_nodes', [sa.text("(properties->>'file_path')")])
    op.create_index('idx_nodes_properties', 'code_nodes', ['properties'], postgresql_using='gin')
    
    # Add comments for code_nodes
    op.execute("""
        COMMENT ON TABLE code_nodes IS 'Stores code entities (functions, classes, modules, etc.) with multi-tenant isolation'
    """)
    op.execute("""
        COMMENT ON COLUMN code_nodes.tenant_id IS 'Tenant identifier for multi-tenant isolation (from AAET-83)'
    """)
    op.execute("""
        COMMENT ON COLUMN code_nodes.repo_id IS 'Repository identifier for multi-repo support (from AAET-83)'
    """)
    op.execute("""
        COMMENT ON COLUMN code_nodes.qualified_name IS 'Fully qualified name of the code entity (e.g., module.Class.method)'
    """)
    op.execute("""
        COMMENT ON COLUMN code_nodes.node_type IS 'Type of code entity (Function, Class, Module, etc.)'
    """)
    op.execute("""
        COMMENT ON COLUMN code_nodes.properties IS 'Full node properties stored as JSONB for flexibility'
    """)
    
    # Create code_edges table
    op.create_table(
        'code_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('from_node', sa.Text(), nullable=False),
        sa.Column('to_node', sa.Text(), nullable=False),
        sa.Column('edge_type', sa.String(length=50), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'from_node', 'to_node', 'edge_type', name='unique_edge_per_tenant')
    )
    
    # Create indexes for code_edges
    op.create_index('idx_edges_tenant_id', 'code_edges', ['tenant_id'])
    op.create_index('idx_edges_from_node', 'code_edges', ['from_node'])
    op.create_index('idx_edges_to_node', 'code_edges', ['to_node'])
    op.create_index('idx_edges_edge_type', 'code_edges', ['edge_type'])
    op.create_index('idx_edges_tenant_from', 'code_edges', ['tenant_id', 'from_node'])
    op.create_index('idx_edges_tenant_to', 'code_edges', ['tenant_id', 'to_node'])
    op.create_index('idx_edges_properties', 'code_edges', ['properties'], postgresql_using='gin')
    
    # Add comments for code_edges
    op.execute("""
        COMMENT ON TABLE code_edges IS 'Stores relationships between code entities (calls, imports, etc.) with multi-tenant isolation'
    """)
    op.execute("""
        COMMENT ON COLUMN code_edges.tenant_id IS 'Tenant identifier for multi-tenant isolation (from AAET-83)'
    """)
    op.execute("""
        COMMENT ON COLUMN code_edges.from_node IS 'Qualified name of the source node'
    """)
    op.execute("""
        COMMENT ON COLUMN code_edges.to_node IS 'Qualified name of the target node'
    """)
    op.execute("""
        COMMENT ON COLUMN code_edges.edge_type IS 'Type of relationship (CALLS, IMPORTS, DEFINES, etc.)'
    """)
    op.execute("""
        COMMENT ON COLUMN code_edges.properties IS 'Additional edge properties stored as JSONB'
    """)
    
    # Create embeddings table
    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('repo_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_id', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=False),  # Will be cast to vector(1024)
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'repo_id', 'chunk_id', name='unique_embedding_per_tenant_repo')
    )
    
    # Cast embedding column to vector(1024) type
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024)")
    
    # Create indexes for embeddings
    op.create_index('idx_embeddings_tenant_id', 'embeddings', ['tenant_id'])
    op.create_index('idx_embeddings_repo_id', 'embeddings', ['repo_id'])
    op.create_index('idx_embeddings_chunk_id', 'embeddings', ['chunk_id'])
    op.create_index('idx_embeddings_tenant_repo', 'embeddings', ['tenant_id', 'repo_id'])
    op.create_index('idx_embeddings_metadata', 'embeddings', ['metadata'], postgresql_using='gin')
    
    # Create IVFFlat index for vector similarity search
    op.execute("""
        CREATE INDEX idx_embeddings_vector 
        ON embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    
    # Add comments for embeddings
    op.execute("""
        COMMENT ON TABLE embeddings IS 'Stores code chunk embeddings with pgvector for semantic search and RAG retrieval'
    """)
    op.execute("""
        COMMENT ON COLUMN embeddings.tenant_id IS 'Tenant identifier for multi-tenant isolation (from AAET-83)'
    """)
    op.execute("""
        COMMENT ON COLUMN embeddings.repo_id IS 'Repository identifier for multi-repo support (from AAET-83)'
    """)
    op.execute("""
        COMMENT ON COLUMN embeddings.chunk_id IS 'Unique identifier for the code chunk'
    """)
    op.execute("""
        COMMENT ON COLUMN embeddings.embedding IS 'Vector embedding (1024 dimensions for Voyage AI voyage-code-3 model) stored using pgvector'
    """)
    op.execute("""
        COMMENT ON COLUMN embeddings.metadata IS 'Additional metadata about the chunk (file_path, node_type, etc.) stored as JSONB'
    """)


def downgrade() -> None:
    """Downgrade database schema."""
    
    # Drop tables in reverse order
    op.drop_table('embeddings')
    op.drop_table('code_edges')
    op.drop_table('code_nodes')
    
    # Note: We don't drop the vector extension as it might be used by other applications
    # op.execute("DROP EXTENSION IF EXISTS vector")
