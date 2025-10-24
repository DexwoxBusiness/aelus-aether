-- Migration: Create embeddings table with pgvector
-- Story: AAET-87 - Integrate code-graph-rag with Celery Tasks
-- Description: Creates table for storing code embeddings with multi-tenant and multi-repo support

-- Enable pgvector extension (already enabled in init-db.sql, but safe to repeat)
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings Table
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    repo_id VARCHAR(36) NOT NULL,
    chunk_id TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure uniqueness per tenant/repo/chunk
    CONSTRAINT unique_embedding_per_tenant_repo UNIQUE (tenant_id, repo_id, chunk_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_embeddings_tenant_id ON embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_repo_id ON embeddings(repo_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_embeddings_tenant_repo ON embeddings(tenant_id, repo_id);

-- IVFFlat index for vector similarity search (cosine distance)
-- Lists parameter: sqrt(total_rows) is a good starting point, 100 for small datasets
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- GIN index for JSONB metadata (enables efficient JSON queries)
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata ON embeddings USING GIN (metadata);

-- Comments for documentation
COMMENT ON TABLE embeddings IS 'Stores code chunk embeddings with pgvector for semantic search and RAG retrieval';

COMMENT ON COLUMN embeddings.tenant_id IS 'Tenant identifier for multi-tenant isolation (from AAET-83)';
COMMENT ON COLUMN embeddings.repo_id IS 'Repository identifier for multi-repo support (from AAET-83)';
COMMENT ON COLUMN embeddings.chunk_id IS 'Unique identifier for the code chunk';
COMMENT ON COLUMN embeddings.embedding IS 'Vector embedding (1024 dimensions for Voyage AI voyage-code-3 model) stored using pgvector';
COMMENT ON COLUMN embeddings.metadata IS 'Additional metadata about the chunk (file_path, node_type, etc.) stored as JSONB';
