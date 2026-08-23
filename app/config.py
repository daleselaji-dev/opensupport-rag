from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration kept outside source code for safe deployment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "lmstudio"
    qdrant_url: str = "http://localhost:6333"
    chat_base_url: str = "http://localhost:1234/v1"
    chat_api_key: str = "lm-studio"
    embedding_provider: str = "lmstudio"
    embedding_base_url: str = "http://localhost:1234/v1"
    embedding_api_key: str = "lm-studio"
    embedding_model: str = "your-embedding-model-id"
    chat_model: str = "your-chat-model-id"
    embedding_family: str = "qwen"
    collection_name: str = "opensupport_v01"
    sparse_collection_name: str = "opensupport_qwen_v02_sparse"
    contextual_collection_name: str = "opensupport_qwen_v05_contextual"
    contextual_sparse_collection_name: str = "opensupport_qwen_v05_contextual_sparse"
    contextual_chunk_chars: int = 1800
    contextual_chunk_overlap: int = 220
    pdf_collection_name: str = "opensupport_qwen_v08_pdf_pages"
    pdf_sparse_collection_name: str = "opensupport_qwen_v08_pdf_pages_sparse"
    sparse_model: str = "qdrant/bm25"
    native_sparse_enabled: bool = True
    guidance_top_k: int = 3
    complaint_top_k: int = 3
    # The answer contract is at most three bullets; keep local R1 latency
    # bounded instead of spending the whole context on hidden verbosity.
    chat_max_tokens: int = 600
    max_context_chars: int = 1000
    citation_repair_max_tokens: int = 300
    # A second local LLM call improves formatting in some cases but can break
    # the end-to-end p95 budget. Production defaults to deterministic grounded
    # fallback; enable this only as an evaluated experiment.
    citation_repair_enabled: bool = False
    min_citation_coverage: float = 0.8
    # V0.4 is an explicit opt-in experiment.  Keep the optional Cross-Encoder
    # out of the baseline path until the frozen benchmark proves a ranking
    # problem and the operator has installed its model dependency.
    reranker_enabled: bool = False
    reranker_provider: str = "llama_cpp"
    reranker_base_url: str = "http://localhost:23146"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"
    reranker_max_length: int = 512
    reranker_candidate_k: int = 50
    reranker_final_k: int = 3
    reranker_timeout_s: float = 120.0
    reranker_batch_size: int = 4
    reranker_text_chars: int = 1800
    data_dir: str = "data"
    data_pipeline_version: str = "v0.0-data-foundation-1"
    postgres_url: str = "postgresql+psycopg://opensupport:opensupport@localhost:15432/opensupport"
    minio_endpoint: str = "localhost:19000"
    minio_access_key: str = "opensupport"
    minio_secret_key: str = "opensupport-dev-secret"
    minio_bucket: str = "opensupport-raw"
    redis_url: str = "redis://localhost:16379/0"
    celery_app_name: str = "opensupport"
    otel_exporter_endpoint: str = "http://localhost:14318"
    prometheus_port: int = 19090
    langfuse_host: str = "http://localhost:13000"
    truth_source_required: bool = False
    storage_probe_enabled: bool = False
    trace_persistence_enabled: bool = False
    otel_enabled: bool = False
    agent_enabled: bool = False
    cache_enabled: bool = True
    cache_ttl_s: int = 300
    embedding_timeout_s: float = 45.0
    chat_timeout_s: float = 120.0
    max_model_concurrency: int = 2
    rate_limit_per_minute: int = 60
    graph_enabled: bool = False
    neo4j_url: str = "bolt://localhost:17687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "opensupport-dev-password"


@lru_cache
def get_settings() -> Settings:
    return Settings()
