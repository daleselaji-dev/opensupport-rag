"""Source-backed frontier RAG module registry.

The registry makes an explicit distinction between "known and interesting"
and "accepted into the production path". Every module needs a problem
hypothesis, a trace contract, a cost budget and a frozen Eval slice.
"""

from __future__ import annotations

FRONTIER_MODULES = [
    {
        "id": "native_hybrid_rrf",
        "version": "v0_2",
        "name": "Native Dense + Sparse/BM25 + RRF",
        "problem": "语义召回漏掉精确术语、规则编号和产品名",
        "source": "https://qdrant.tech/documentation/search/hybrid-queries/",
        "trace_added": ["sparse_backend", "bm25_guidance", "bm25_complaints", "fusion_rrf"],
        "status": "implemented",
        "entry_gate": "同一快照上 Recall/MRR/nDCG 与延迟对照",
    },
    {
        "id": "query_translation",
        "version": "v0_6",
        "name": "Rewrite / Multi-query / Decomposition / HyDE",
        "problem": "用户问题模糊、复合或不适合直接检索",
        "source": "https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-information-retrieval",
        "trace_added": ["adaptive_route", "evidence_grade", "query_translation", "corrective_retry"],
        "status": "experimental",
        "implementation": "V0.6 bounded evidence grade + one deterministic domain-term retry 已实现",
        "entry_gate": "失败切片证明原 Query 变换能提高召回，且重试预算可控",
    },
    {
        "id": "contextual_retrieval",
        "version": "v0_5",
        "name": "Contextual Embeddings + Contextual BM25",
        "problem": "Chunk 脱离标题、章节、时间和文档主体后无法理解",
        "source": "https://www.anthropic.com/engineering/contextual-retrieval",
        "trace_added": ["contextualize_chunk", "retrieve_child", "expand_parent", "budget_context"],
        "status": "experimental",
        "implementation": "V0.5 deterministic contextual prefix + parent-child index 已实现；默认不覆盖旧索引",
        "last_eval": "12,335-point snapshot：Hit@3 0.975；MRR 0.8958；p95 174.15ms；19,087 contextual chunks",
        "entry_gate": "长文档/孤立 Chunk 切片 Citation Support 改善，预处理成本可记录",
    },
    {
        "id": "cross_encoder_reranker",
        "version": "v0_4",
        "name": "Cross-Encoder Reranker",
        "problem": "正确证据进入候选集但排名靠后",
        "source": "https://aclanthology.org/2025.findings-emnlp.218/",
        "secondary_source": "https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-information-retrieval",
        "trace_added": ["rerank_candidates", "select_evidence"],
        "status": "experimental",
        "implementation": "已实现 llama.cpp 本地 Reranker 适配器；默认关闭，需同集 Eval 后才进入主链路",
        "last_eval": "消融：k=10 MRR 0.9375/p95 5346ms；k=20 MRR 1.0/p95 9908ms；V0.3 Hybrid MRR 1.0/p95 81ms，暂不晋级",
        "entry_gate": "候选集 Recall 已足够且排名问题在 Golden Set 中重复出现",
    },
    {
        "id": "graph_global_local",
        "version": "v0_7",
        "name": "GraphRAG / DRIFT / Dynamic Community Selection",
        "problem": "全局主题、多跳关系和跨文档聚合不是普通 Top-k 检索问题",
        "source": "https://www.microsoft.com/en-us/research/project/graphrag/overview/",
        "trace_added": ["graph_route", "entity_link", "community_select", "graph_evidence"],
        "status": "experimental",
        "implementation": "Neo4j Community profile 已运行；已写入结构化 CFPB Complaint/Product/Issue/Company 关系，未让 LLM 创造事实关系",
        "last_eval": "Graph smoke：12,223 Complaint、112 Source、41,802 structured relationships；尚未完成全局主题 Golden Set",
        "entry_gate": "只在 Support Intelligence 全局问题切片上比较，必须追溯实体和原始来源",
    },
    {
        "id": "multimodal_page_retrieval",
        "version": "v0_8",
        "name": "Page-level Multimodal Retrieval",
        "problem": "PDF 表格、图表、布局信息在纯 OCR/文本 Chunk 中丢失",
        "source": "https://proceedings.iclr.cc/paper_files/paper/2025/hash/99e9e141aafc314f76b0ca3dd66898b3-Abstract-Conference.html",
        "trace_added": ["detect_modality", "render_pdf", "visual_retrieve", "extract_region"],
        "status": "experimental",
        "implementation": "V0.8 页级 pypdf 文本基线已实现，保留 page metadata；Docling/MinerU/视觉区域检索仍未进入默认链路",
        "last_eval": "官方 CFPB PDF CDN 当前 403；因此不宣称视觉表格/图表 Recall",
        "entry_gate": "页面级 Recall 与真实表格/图表问题的引用正确性可复现",
    },
    {
        "id": "agentic_retrieval",
        "version": "v1_0",
        "name": "Bounded Agentic Retrieval",
        "problem": "复杂问题需要多查询、证据评估和有限重试",
        "source": "https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview",
        "trace_added": ["plan_subqueries", "tool_search", "grade_evidence", "stop_or_retry"],
        "status": "locked",
        "entry_gate": "纯 RAG 的数据、检索、回答、安全和运维 Gate 全通过；工具不执行外部动作",
    },
]


def frontier_modules() -> list[dict[str, object]]:
    return [dict(module) for module in FRONTIER_MODULES]
