-- ADR-0049: Multi-Agent LLM Memory Architecture
-- PgVector Schema for RAG and Troubleshooting Memory
--
-- This script runs automatically on PostgreSQL container startup
-- via docker-entrypoint-initdb.d mount

-- =============================================================================
-- Enable PgVector Extension
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extension is loaded
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension not available';
    END IF;
    RAISE NOTICE 'pgvector extension enabled successfully';
END $$;

-- =============================================================================
-- RAG Documents Table
-- =============================================================================
-- Stores document embeddings for semantic search
-- Supports: ADRs, provider docs, DAG examples, troubleshooting guides

CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Content
    content TEXT NOT NULL,
    content_hash VARCHAR(64),  -- SHA256 for deduplication

    -- Embedding (384 dimensions for MiniLM-L6, can be adjusted)
    embedding vector(384),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    doc_type VARCHAR(50) NOT NULL,  -- 'adr', 'provider_doc', 'dag', 'troubleshooting', 'guide'
    source_path TEXT,
    source_url TEXT,

    -- Chunking info
    chunk_index INTEGER DEFAULT 0,
    parent_doc_id UUID,  -- Reference to parent if this is a chunk

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_doc_type CHECK (doc_type IN (
        'adr', 'provider_doc', 'dag', 'troubleshooting',
        'guide', 'policy', 'example', 'api_doc', 'readme'
    ))
);

-- Index for vector similarity search (IVFFlat for performance)
-- lists = 100 is good for up to ~100k documents
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
    ON rag_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for filtering by doc_type
CREATE INDEX IF NOT EXISTS idx_rag_documents_doc_type
    ON rag_documents (doc_type);

-- Index for content hash (deduplication)
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_hash
    ON rag_documents (content_hash);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata
    ON rag_documents USING GIN (metadata);

-- =============================================================================
-- Troubleshooting Attempts Table
-- =============================================================================
-- Records all troubleshooting attempts for learning
-- Enables: "What worked before for this error?"

CREATE TABLE IF NOT EXISTS troubleshooting_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Session tracking
    session_id UUID NOT NULL,
    sequence_num INTEGER DEFAULT 1,  -- Order within session

    -- Problem description
    task_description TEXT NOT NULL,
    error_message TEXT,
    error_category VARCHAR(100),  -- 'dns', 'firewall', 'permission', 'config', etc.

    -- Solution attempted
    attempted_solution TEXT NOT NULL,
    solution_type VARCHAR(50),  -- 'command', 'config_change', 'code_fix', 'restart'

    -- Outcome
    result VARCHAR(20) NOT NULL,  -- 'success', 'failed', 'partial'
    result_details TEXT,

    -- Embedding for similarity search
    embedding vector(384),

    -- Confidence and attribution
    confidence_score FLOAT,
    agent VARCHAR(50),  -- 'developer', 'manager', 'calling_llm'
    override_by VARCHAR(50),  -- NULL if no override, else who overrode
    override_reason TEXT,

    -- Context
    dag_id VARCHAR(250),
    component VARCHAR(100),  -- 'freeipa', 'vyos', 'openshift', etc.

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_result CHECK (result IN ('success', 'failed', 'partial')),
    CONSTRAINT valid_agent CHECK (agent IN ('developer', 'manager', 'calling_llm', 'user'))
);

-- Index for similarity search on error patterns
CREATE INDEX IF NOT EXISTS idx_troubleshooting_embedding
    ON troubleshooting_attempts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- Index for session queries
CREATE INDEX IF NOT EXISTS idx_troubleshooting_session
    ON troubleshooting_attempts (session_id, sequence_num);

-- Index for component-based queries
CREATE INDEX IF NOT EXISTS idx_troubleshooting_component
    ON troubleshooting_attempts (component, error_category);

-- Index for finding successful solutions
CREATE INDEX IF NOT EXISTS idx_troubleshooting_success
    ON troubleshooting_attempts (result, error_category)
    WHERE result = 'success';

-- =============================================================================
-- Agent Decisions Table
-- =============================================================================
-- Logs all decisions made by agents for auditing and learning

CREATE TABLE IF NOT EXISTS agent_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Agent info
    agent VARCHAR(50) NOT NULL,  -- 'developer', 'manager', 'calling_llm'
    decision_type VARCHAR(50) NOT NULL,  -- 'task_execution', 'escalation', 'override', 'provider_check'

    -- Decision context
    context JSONB NOT NULL,  -- Full context at decision time

    -- Decision details
    decision TEXT NOT NULL,
    reasoning TEXT,

    -- Confidence metrics
    confidence FLOAT,
    rag_hits INTEGER,  -- How many RAG documents were found
    rag_max_similarity FLOAT,  -- Best similarity score

    -- Outcome (updated after execution)
    outcome VARCHAR(20),  -- 'success', 'failed', 'pending'
    outcome_details TEXT,

    -- Session tracking
    session_id UUID,
    parent_decision_id UUID,  -- For decision chains

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_decision_agent CHECK (agent IN ('developer', 'manager', 'calling_llm')),
    CONSTRAINT valid_decision_type CHECK (decision_type IN (
        'task_execution', 'escalation', 'override', 'provider_check',
        'rag_query', 'confidence_check', 'delegation', 'plan_creation'
    ))
);

-- Index for session queries
CREATE INDEX IF NOT EXISTS idx_agent_decisions_session
    ON agent_decisions (session_id, created_at);

-- Index for agent analysis
CREATE INDEX IF NOT EXISTS idx_agent_decisions_agent
    ON agent_decisions (agent, decision_type);

-- Index for low confidence decisions (for review)
CREATE INDEX IF NOT EXISTS idx_agent_decisions_low_confidence
    ON agent_decisions (confidence)
    WHERE confidence < 0.6;

-- =============================================================================
-- Provider Registry Table
-- =============================================================================
-- Cache of known Airflow providers for Provider-First Rule

CREATE TABLE IF NOT EXISTS airflow_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Provider info
    provider_name VARCHAR(100) NOT NULL UNIQUE,  -- e.g., 'apache-airflow-providers-microsoft-azure'
    package_name VARCHAR(100) NOT NULL,

    -- Capabilities
    operators JSONB DEFAULT '[]',  -- List of operators
    hooks JSONB DEFAULT '[]',  -- List of hooks
    sensors JSONB DEFAULT '[]',  -- List of sensors

    -- Metadata
    description TEXT,
    documentation_url TEXT,
    version VARCHAR(20),

    -- Status
    is_installed BOOLEAN DEFAULT FALSE,
    last_checked TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for provider lookup
CREATE INDEX IF NOT EXISTS idx_airflow_providers_name
    ON airflow_providers (provider_name);

-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Function to search similar documents
CREATE OR REPLACE FUNCTION search_similar_documents(
    query_embedding vector(384),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INTEGER DEFAULT 5,
    filter_doc_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    doc_type VARCHAR,
    source_path TEXT,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.doc_type,
        d.source_path,
        1 - (d.embedding <=> query_embedding) AS similarity,
        d.metadata
    FROM rag_documents d
    WHERE
        (filter_doc_type IS NULL OR d.doc_type = filter_doc_type)
        AND 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to search similar troubleshooting attempts
CREATE OR REPLACE FUNCTION search_similar_errors(
    query_embedding vector(384),
    match_threshold FLOAT DEFAULT 0.6,
    match_count INTEGER DEFAULT 5,
    only_successful BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    id UUID,
    error_message TEXT,
    attempted_solution TEXT,
    result VARCHAR,
    component VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.error_message,
        t.attempted_solution,
        t.result,
        t.component,
        1 - (t.embedding <=> query_embedding) AS similarity
    FROM troubleshooting_attempts t
    WHERE
        t.embedding IS NOT NULL
        AND 1 - (t.embedding <=> query_embedding) > match_threshold
        AND (NOT only_successful OR t.result = 'success')
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to compute confidence score
CREATE OR REPLACE FUNCTION compute_confidence_score(
    rag_similarity FLOAT,
    rag_hit_count INTEGER,
    provider_exists BOOLEAN,
    similar_dag_exists BOOLEAN
)
RETURNS FLOAT AS $$
BEGIN
    RETURN (
        0.4 * COALESCE(rag_similarity, 0) +
        0.3 * LEAST(COALESCE(rag_hit_count, 0)::FLOAT / 5.0, 1.0) +
        0.2 * (CASE WHEN provider_exists THEN 1.0 ELSE 0.0 END) +
        0.1 * (CASE WHEN similar_dag_exists THEN 1.0 ELSE 0.0 END)
    );
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Initial Data: Common Airflow Providers
-- =============================================================================

INSERT INTO airflow_providers (provider_name, package_name, description, documentation_url) VALUES
    ('postgres', 'apache-airflow-providers-postgres', 'PostgreSQL provider', 'https://airflow.apache.org/docs/apache-airflow-providers-postgres/stable/index.html'),
    ('ssh', 'apache-airflow-providers-ssh', 'SSH provider for remote execution', 'https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/index.html'),
    ('http', 'apache-airflow-providers-http', 'HTTP provider for REST APIs', 'https://airflow.apache.org/docs/apache-airflow-providers-http/stable/index.html'),
    ('kubernetes', 'apache-airflow-providers-cncf-kubernetes', 'Kubernetes provider', 'https://airflow.apache.org/docs/apache-airflow-providers-cncf-kubernetes/stable/index.html'),
    ('docker', 'apache-airflow-providers-docker', 'Docker provider', 'https://airflow.apache.org/docs/apache-airflow-providers-docker/stable/index.html'),
    ('amazon', 'apache-airflow-providers-amazon', 'AWS provider', 'https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/index.html'),
    ('google', 'apache-airflow-providers-google', 'GCP provider', 'https://airflow.apache.org/docs/apache-airflow-providers-google/stable/index.html'),
    ('microsoft-azure', 'apache-airflow-providers-microsoft-azure', 'Azure provider', 'https://airflow.apache.org/docs/apache-airflow-providers-microsoft-azure/stable/index.html'),
    ('openlineage', 'apache-airflow-providers-openlineage', 'OpenLineage lineage tracking', 'https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/index.html'),
    ('slack', 'apache-airflow-providers-slack', 'Slack notifications', 'https://airflow.apache.org/docs/apache-airflow-providers-slack/stable/index.html'),
    ('redis', 'apache-airflow-providers-redis', 'Redis provider', 'https://airflow.apache.org/docs/apache-airflow-providers-redis/stable/index.html'),
    ('elasticsearch', 'apache-airflow-providers-elasticsearch', 'Elasticsearch provider', 'https://airflow.apache.org/docs/apache-airflow-providers-elasticsearch/stable/index.html')
ON CONFLICT (provider_name) DO NOTHING;

-- =============================================================================
-- Verification
-- =============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('rag_documents', 'troubleshooting_attempts', 'agent_decisions', 'airflow_providers');

    IF table_count = 4 THEN
        RAISE NOTICE 'ADR-0049 schema created successfully: % tables', table_count;
    ELSE
        RAISE WARNING 'Expected 4 tables, found %', table_count;
    END IF;
END $$;
