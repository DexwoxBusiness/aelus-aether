-- Initialize PostgreSQL database for aelus-aether

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database (if running manually, not needed in docker-entrypoint-initdb.d)
-- CREATE DATABASE aelus_aether;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE aelus_aether TO aelus;

-- Note: Tables will be created by SQLAlchemy/Alembic migrations
