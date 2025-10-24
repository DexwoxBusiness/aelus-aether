-- Migration: Create code graph tables for PostgreSQL
-- Story: AAET-84 - Abstract Storage Interface
-- Description: Creates tables for storing code nodes and edges with multi-tenant support

-- Enable JSONB support (should be available by default in modern PostgreSQL)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Code Nodes Table
CREATE TABLE IF NOT EXISTS code_nodes (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    repo_id VARCHAR(36) NOT NULL,
    qualified_name TEXT NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    properties JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure uniqueness per tenant/repo/qualified_name
    CONSTRAINT unique_node_per_tenant UNIQUE (tenant_id, repo_id, qualified_name)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_nodes_tenant_id ON code_nodes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_nodes_repo_id ON code_nodes(repo_id);
CREATE INDEX IF NOT EXISTS idx_nodes_qualified_name ON code_nodes(qualified_name);
CREATE INDEX IF NOT EXISTS idx_nodes_node_type ON code_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_file_path ON code_nodes((properties->>'file_path'));

-- GIN index for JSONB properties (enables efficient JSON queries)
CREATE INDEX IF NOT EXISTS idx_nodes_properties ON code_nodes USING GIN (properties);

-- Code Edges Table
CREATE TABLE IF NOT EXISTS code_edges (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    properties JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure uniqueness per tenant/from/to/type
    CONSTRAINT unique_edge_per_tenant UNIQUE (tenant_id, from_node, to_node, edge_type)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_edges_tenant_id ON code_edges(tenant_id);
CREATE INDEX IF NOT EXISTS idx_edges_from_node ON code_edges(from_node);
CREATE INDEX IF NOT EXISTS idx_edges_to_node ON code_edges(to_node);
CREATE INDEX IF NOT EXISTS idx_edges_edge_type ON code_edges(edge_type);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_edges_tenant_from ON code_edges(tenant_id, from_node);
CREATE INDEX IF NOT EXISTS idx_edges_tenant_to ON code_edges(tenant_id, to_node);

-- GIN index for JSONB properties
CREATE INDEX IF NOT EXISTS idx_edges_properties ON code_edges USING GIN (properties);

-- Comments for documentation
COMMENT ON TABLE code_nodes IS 'Stores code entities (functions, classes, modules, etc.) with multi-tenant isolation';
COMMENT ON TABLE code_edges IS 'Stores relationships between code entities (calls, imports, etc.) with multi-tenant isolation';

COMMENT ON COLUMN code_nodes.tenant_id IS 'Tenant identifier for multi-tenant isolation (from AAET-83)';
COMMENT ON COLUMN code_nodes.repo_id IS 'Repository identifier for multi-repo support (from AAET-83)';
COMMENT ON COLUMN code_nodes.qualified_name IS 'Fully qualified name of the code entity (e.g., module.Class.method)';
COMMENT ON COLUMN code_nodes.node_type IS 'Type of code entity (Function, Class, Module, etc.)';
COMMENT ON COLUMN code_nodes.properties IS 'Full node properties stored as JSONB for flexibility';

COMMENT ON COLUMN code_edges.tenant_id IS 'Tenant identifier for multi-tenant isolation (from AAET-83)';
COMMENT ON COLUMN code_edges.from_node IS 'Qualified name of the source node';
COMMENT ON COLUMN code_edges.to_node IS 'Qualified name of the target node';
COMMENT ON COLUMN code_edges.edge_type IS 'Type of relationship (CALLS, IMPORTS, DEFINES, etc.)';
COMMENT ON COLUMN code_edges.properties IS 'Additional edge properties stored as JSONB';
