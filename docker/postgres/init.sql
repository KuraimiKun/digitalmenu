-- PostgreSQL initialization script
-- This script runs when the database container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create default schema if needed
-- CREATE SCHEMA IF NOT EXISTS digitalmenu;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE digitalmenu TO digitalmenu;
