-- OpenSupport V0.0 source-of-truth schema.
-- Qdrant is a derived read model; these tables remain the rebuildable record.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('guidance', 'regulation', 'complaint')),
    external_id TEXT,
    title TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_type, external_id),
    UNIQUE (source_type, canonical_url)
);

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES source_documents(id),
    content_sha256 TEXT NOT NULL,
    raw_object_key TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    lifecycle_status TEXT NOT NULL DEFAULT 'discovered',
    parser_name TEXT,
    parser_version TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (document_id, content_sha256)
);

CREATE TABLE IF NOT EXISTS parsed_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_version_id UUID NOT NULL REFERENCES document_versions(id),
    block_order INTEGER NOT NULL,
    block_type TEXT NOT NULL,
    heading_path TEXT[] NOT NULL DEFAULT '{}',
    text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (document_version_id, block_order)
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_version_id UUID NOT NULL REFERENCES document_versions(id),
    parent_chunk_id TEXT,
    chunk_order INTEGER NOT NULL,
    text TEXT NOT NULL,
    normalized_text_sha256 TEXT NOT NULL,
    language TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    lifecycle_status TEXT NOT NULL DEFAULT 'chunked',
    UNIQUE (document_version_id, chunk_order)
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_limit INTEGER,
    requested_year INTEGER,
    status TEXT NOT NULL DEFAULT 'discovered',
    snapshot_id TEXT,
    accepted_documents INTEGER NOT NULL DEFAULT 0,
    duplicate_documents INTEGER NOT NULL DEFAULT 0,
    quarantined_documents INTEGER NOT NULL DEFAULT 0,
    indexed_documents INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS index_versions (
    index_version TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    collection_name TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    sparse_model TEXT,
    chunking_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'building',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS index_memberships (
    index_version TEXT NOT NULL REFERENCES index_versions(index_version),
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
    qdrant_point_id TEXT NOT NULL,
    PRIMARY KEY (index_version, chunk_id)
);

CREATE TABLE IF NOT EXISTS eval_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_version TEXT NOT NULL,
    assembly_version TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    gates JSONB NOT NULL DEFAULT '[]'::jsonb,
    report_object_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trace_spans (
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,
    component TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms NUMERIC,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trace_id, span_id)
);

CREATE TABLE IF NOT EXISTS agent_drafts (
    draft_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_approval',
    payload JSONB NOT NULL,
    approved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ
);
