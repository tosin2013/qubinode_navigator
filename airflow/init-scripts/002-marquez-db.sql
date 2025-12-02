-- =============================================================================
-- Marquez Database Setup
-- =============================================================================
-- Creates separate database and user for Marquez lineage tracking
-- This runs on PostgreSQL startup via docker-entrypoint-initdb.d
-- SQL files run as the POSTGRES_USER (airflow)

-- Create marquez user
CREATE USER marquez WITH PASSWORD 'marquez';

-- Create marquez database
CREATE DATABASE marquez OWNER marquez;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE marquez TO marquez;
