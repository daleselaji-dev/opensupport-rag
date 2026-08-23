from contextlib import asynccontextmanager
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.cfpb import fetch_credit_card_complaints, fetch_official_guidance, load_cfpb_mirror_csv, load_credit_card_complaints_csv
from app.config import get_settings
from app.answer_eval import load_last_answer_eval, run_answer_eval
from app.agent import ComplaintAgent
from app.data_foundation import finalize_quality_report, load_quality_report, prepare_documents, save_quality_report
from app.eval import load_last_eval, run_retrieval_eval
from app.lifecycle import build_lifecycle
from app.rag import DependencyNotReady, RagService
from app.reranker import RerankerUnavailable
from app.rate_limit import SlidingWindowLimiter
from app.graph import GraphStore
from app.celery_app import celery_app
from app.storage import SourceOfTruthStore
from app.observability import configure_otel, metrics_payload, observe_request, tracer
from app.frontier import frontier_modules
from app.schemas import AgentRequest, AgentResponse, IndexActivationRequest, IngestRequest, IngestResponse, LocalIngestRequest, QueryRequest, QueryResponse, RetrievalPreviewResponse, TraceEvent

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
QUALITY_REPORT = DATA / "data_quality_latest.json"
INGEST_FAILURE = DATA / "ingest_failure_latest.json"
logger = logging.getLogger("opensupport.api")

if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    # psycopg's async driver cannot run on Windows' default Proactor loop.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_otel(get_settings())
    app.state.rag = RagService(get_settings())
    app.state.storage = SourceOfTruthStore(get_settings())
    app.state.graph = GraphStore(get_settings())
    yield
    await app.state.graph.close()
    await app.state.rag.close()


app = FastAPI(title="OpenSupport RAG", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
rate_limiter = SlidingWindowLimiter(get_settings().rate_limit_per_minute)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    started = time.perf_counter()
    if request.url.path.startswith("/api/") and request.url.path not in {"/api/health", "/api/data-quality"}:
        client_key = request.client.host if request.client else "unknown"
        allowed, retry_after = rate_limiter.allow(client_key)
        if not allowed:
            observe_request(request.method, request.url.path, 429, started)
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试。", "retry_after_s": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
    span = tracer().start_as_current_span(f"{request.method} {request.url.path}") if tracer() is not None else None
    try:
        if span is None:
            response = await call_next(request)
        else:
            with span as active_span:
                response = await call_next(request)
                active_span.set_attribute("http.status_code", response.status_code)
    except Exception:
        observe_request(request.method, request.url.path, 500, started)
        raise
    observe_request(request.method, request.url.path, response.status_code, started)
    return response


@app.get("/")
async def home():
    return FileResponse(STATIC / "index.html")


@app.get("/metrics")
async def metrics():
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)


@app.get("/api/health")
async def health():
    status = await app.state.rag.health()
    status["storage"] = await app.state.storage.health()
    status["graph"] = await app.state.graph.health()
    return status


@app.get("/api/eval/last")
async def eval_last():
    return load_last_eval() or {"status": "not_run", "message": "尚未运行 V0.2 seed retrieval eval。"}


@app.get("/api/data-quality")
async def data_quality():
    report = load_quality_report(QUALITY_REPORT)
    if report is None:
        response = {
            "status": "not_run",
            "message": "尚未运行 V0.0 Data Foundation；导入数据后这里会显示清洗、去重、隔离和索引状态。",
        }
        if INGEST_FAILURE.exists():
            try:
                response["last_failure"] = json.loads(INGEST_FAILURE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                response["last_failure"] = {"message": "最近一次数据源下载失败，但失败详情文件无法读取。"}
        return response
    return report


@app.get("/api/frontier/modules")
async def frontier_module_catalog():
    return {"modules": frontier_modules(), "principle": "没有同集 Eval 证据的模块不会自动进入默认主链路。"}


@app.get("/api/agent/status")
async def agent_status():
    return {
        "version": "v1.0-controlled",
        "status": "available" if get_settings().agent_enabled else "locked",
        "allowed_tools": ["search_complaints", "search_guidance", "build_ticket_draft"],
        "forbidden_actions": ["send_customer_message", "write_external_crm", "promise_refund", "decide_legal_liability"],
        "approval_required": True,
    }


@app.post("/api/agent/run", response_model=AgentResponse)
async def agent_run(request: AgentRequest):
    if not get_settings().agent_enabled:
        raise HTTPException(status_code=423, detail="V1 受控 Agent 尚未开放；请先完成 V0.4–V0.9 的数据、检索、答案、安全和运维 Gate。")
    trace_id = app.state.rag.new_trace_id()
    try:
        response = await ComplaintAgent(app.state.rag).run(request, trace_id)
        if response.draft is not None:
            storage_result = await app.state.storage.persist_agent_draft(
                response.draft.draft_id,
                trace_id,
                response.draft.model_dump(mode="json"),
            )
            response.trace.append(
                TraceEvent(
                    step=len(response.trace) + 1,
                    name="persist_agent_draft",
                    status="completed" if storage_result.get("status") == "persisted" else "pending",
                    duration_ms=0.0,
                    summary="草稿已写入本地待审批队列" if storage_result.get("status") == "persisted" else "草稿未写入数据库",
                    details=storage_result,
                )
            )
        try:
            await app.state.storage.persist_trace(trace_id, response.trace)
        except Exception as trace_error:
            logger.warning("agent trace persistence skipped: %s", trace_error)
        return response
    except RuntimeError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("agent run failed")
        raise HTTPException(status_code=503, detail="受控 Agent 运行失败：请检查检索、模型和 PostgreSQL 状态。") from exc


@app.post("/api/agent/drafts/{draft_id}/approve")
async def approve_agent_draft(draft_id: str, approved_by: str = Query(min_length=2, max_length=120)):
    try:
        return await app.state.storage.approve_agent_draft(draft_id, approved_by)
    except RuntimeError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc


@app.post("/api/index/migrate-sparse")
async def migrate_sparse():
    try:
        migrated = await app.state.rag.migrate_existing_to_sparse()
        return {
            "status": "ready",
            "migrated_documents": migrated,
            "collection_name": get_settings().sparse_collection_name,
            "sparse_model": get_settings().sparse_model,
        }
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RerankerUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("sparse migration failed")
        raise HTTPException(status_code=503, detail="Sparse 索引迁移失败：请检查 Qdrant 版本和当前 Dense 集合。") from exc


@app.post("/api/index/build-contextual")
async def build_contextual_index():
    """Build isolated V0.5 contextual/parent-child indexes from the current truth-derived read model."""

    try:
        return {"status": "ready", **await app.state.rag.build_contextual_index()}
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("contextual index build failed")
        raise HTTPException(status_code=503, detail="V0.5 contextual 索引构建失败：请检查 Embedding、Qdrant 和当前 Dense 索引。") from exc


@app.post("/api/index/build-contextual-async")
async def build_contextual_index_async():
    if celery_app is None:
        raise HTTPException(status_code=424, detail="Celery 未安装或 Worker 未配置，请启动 core profile。")
    task = celery_app.send_task("opensupport.pipeline.build_contextual_index")
    return {"status": "queued", "task_id": task.id, "queue": "celery"}


@app.get("/api/tasks/{task_id}")
async def task_status(task_id: str):
    if celery_app is None:
        raise HTTPException(status_code=424, detail="Celery 未安装或 Worker 未配置。")
    result = celery_app.AsyncResult(task_id)
    payload: dict[str, object] = {"task_id": task_id, "state": result.state}
    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result)
    return payload


@app.get("/api/index/alias")
async def index_alias():
    return app.state.rag.index_registry.read()


@app.post("/api/index/activate")
async def activate_index(request: IndexActivationRequest):
    allowed = {
        get_settings().collection_name: get_settings().sparse_collection_name,
        get_settings().contextual_collection_name: get_settings().contextual_sparse_collection_name,
    }
    if request.collection not in allowed or allowed[request.collection] != request.sparse_collection:
        raise HTTPException(status_code=400, detail="只能激活项目已登记的 Dense/Sparse 集合对。")
    if not await app.state.rag.qdrant.collection_exists(request.collection) or not await app.state.rag.qdrant.collection_exists(request.sparse_collection):
        raise HTTPException(status_code=424, detail="目标索引集合不存在或尚未构建完成。")
    return {"status": "active", **app.state.rag.index_registry.activate(request.collection, request.sparse_collection, reason=request.reason)}


@app.post("/api/index/rollback")
async def rollback_index():
    try:
        current = app.state.rag.index_registry.read()
        previous = list(current.get("previous", []))
        if not previous:
            raise RuntimeError("没有可回滚的上一版索引 Alias。")
        target = previous[0]
        if not await app.state.rag.qdrant.collection_exists(target["active_collection"]) or not await app.state.rag.qdrant.collection_exists(target["active_sparse_collection"]):
            raise RuntimeError("回滚目标集合不存在，未切换 Alias。")
        payload = app.state.rag.index_registry.rollback()
        return {"status": "rolled_back", **payload}
    except RuntimeError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc


@app.post("/api/index/build-graph")
async def build_graph_index():
    try:
        active_collection, _ = app.state.rag.index_registry.active()
        records: list[dict[str, object]] = []
        offset = None
        while True:
            points, offset = await app.state.rag.qdrant.scroll(
                collection_name=active_collection,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            records.extend(dict(point.payload or {}) for point in points)
            if offset is None:
                break
        return {"status": "ready", "source_records": len(records), **await app.state.graph.build_from_records(records)}
    except RuntimeError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("graph build failed")
        raise HTTPException(status_code=503, detail="Graph 索引构建失败：请检查 Neo4j profile。") from exc


@app.post("/api/index/build-pdf-pages")
async def build_pdf_pages(filename: str = Query(..., min_length=1, max_length=200), source_url: str | None = Query(default=None, max_length=500), title: str | None = Query(default=None, max_length=300)):
    raw_dir = (DATA / "raw").resolve()
    path = (raw_dir / filename).resolve()
    if path.parent != raw_dir or path.suffix.lower() != ".pdf" or not path.exists():
        raise HTTPException(status_code=400, detail="PDF 页面索引只允许读取 data/raw 下已存在的 PDF。")
    try:
        return {"status": "ready", **await app.state.rag.build_pdf_index(str(path), source_url=source_url, title=title)}
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("pdf page index build failed")
        raise HTTPException(status_code=503, detail="PDF 页面索引构建失败：请检查 PDF 解析和 Embedding 服务。") from exc


@app.get("/api/graph/query")
async def graph_query(kind: str = Query(default="top_issues", pattern="^(top_issues|top_products)$"), limit: int = Query(default=10, ge=1, le=50)):
    try:
        return {"query_kind": kind, "results": await app.state.graph.query(kind, limit)}
    except RuntimeError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc


@app.get("/api/lifecycle")
async def lifecycle():
    health_state = await app.state.rag.health()
    return build_lifecycle(health_state, load_last_eval(), load_last_answer_eval("v0_2"))


@app.post("/api/eval/run")
async def eval_run(
    retrieval_mode: str = Query(default="dense", pattern="^(dense|hybrid)$"),
    assembly_version: str = Query(default="v0_3", pattern="^v0_[1234568]$"),
    benchmark_version: str = Query(default="v0_2", pattern="^v0_[23]$"),
):
    try:
        return await run_retrieval_eval(app.state.rag, retrieval_mode, assembly_version, benchmark_version)
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RerankerUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Eval 失败：请确认 LM Studio Embedding、Qdrant 和索引均已就绪。") from exc


@app.post("/api/eval/answer-run")
async def answer_eval_run(
    assembly_version: str = Query(default="v0_3", pattern="^v0_[1234568]$"),
    benchmark_version: str = Query(default="v0_2", pattern="^v0_[23]$"),
    max_cases: int | None = Query(default=None, ge=1, le=50),
):
    try:
        return await run_answer_eval(app.state.rag, assembly_version, benchmark_version, max_cases)
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RerankerUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("answer eval failed")
        raise HTTPException(status_code=503, detail="回答 Eval 失败：请确认 LM Studio Chat、Embedding、Qdrant 和索引均已就绪。") from exc


@app.get("/api/eval/answer-last")
async def answer_eval_last(benchmark_version: str = Query(default="v0_2", pattern="^v0_[23]$")):
    return load_last_answer_eval(benchmark_version) or {"status": "not_run", "message": "尚未运行回答/安全 Eval。"}


async def _complete_ingest(
    complaints: list,
    guidance: list,
    guidance_failures: list[str],
    requested_limit: int,
    year: int | str,
) -> IngestResponse:
    """Run the shared quality → index → manifest contract for API and CSV input."""

    if not guidance:
        raise DependencyNotReady("官方指导当前无法获取；请稍后重试，或检查网络是否允许访问 CFPB 官方来源。")
    raw_documents = [record.to_document() for record in complaints] + guidance
    documents, quality = prepare_documents(raw_documents)
    if not documents:
        raise DependencyNotReady("所有来源都未通过数据质量检查，未写入向量索引。请先查看 Data Quality 报告。")
    batch_indexed = await app.state.rag.ingest(documents)
    collection_indexed = await app.state.rag.count()
    quality = finalize_quality_report(quality, collection_indexed, batch_indexed)
    storage = await app.state.storage.persist_ingestion(
        documents,
        quality,
        collection_indexed,
        get_settings().collection_name,
        get_settings().embedding_model,
    )
    DATA.mkdir(exist_ok=True)
    manifest_path = DATA / "ingest_manifest.json"
    save_quality_report(quality, QUALITY_REPORT)
    manifest_path.write_text(
        json.dumps(
            {
                "year": year,
                "requested_complaints": requested_limit,
                "complaint_ids": [record.complaint_id for record in complaints],
                "guidance_urls": sorted({document.source_url for document in guidance}),
                "indexed_documents": collection_indexed,
                "batch_indexed_documents": batch_indexed,
                "collection_indexed_documents": collection_indexed,
                "snapshot_id": quality.snapshot_id,
                "pipeline_version": quality.pipeline_version,
                "accepted_documents": quality.accepted_documents,
                "duplicate_documents": quality.duplicate_documents,
                "quarantined_documents": quality.quarantined_documents,
                "document_hashes": sorted(str(document.metadata.get("content_sha256")) for document in documents),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return IngestResponse(
        requested_complaints=requested_limit,
        fetched_complaints=len(complaints),
        guidance_documents=len(guidance),
        indexed_documents=collection_indexed,
        collection_name=get_settings().collection_name,
        manifest_path=str(manifest_path.relative_to(ROOT)),
        guidance_fetch_failures=guidance_failures,
        snapshot_id=quality.snapshot_id,
        quality_report_path=str(QUALITY_REPORT.relative_to(ROOT)),
        quality=quality,
        storage=storage,
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    try:
        complaints = await fetch_credit_card_complaints(request.limit, request.year)
        guidance, guidance_failures = await fetch_official_guidance()
        return await _complete_ingest(complaints, guidance, guidance_failures, request.limit, request.year)
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning("ingest source unavailable: %s", exc)
        DATA.mkdir(exist_ok=True)
        INGEST_FAILURE.write_text(
            json.dumps(
                {
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "stage": "source_download",
                    "error": str(exc),
                    "next_action": "稍后重试或将官方 CSV 放入 data/raw 后调用 /api/ingest-local",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        raise HTTPException(status_code=503, detail=f"导入数据源暂不可用：{exc}") from exc
    except Exception as exc:
        logger.exception("ingest failed")
        raise HTTPException(status_code=503, detail="导入失败：请检查 CFPB 网络、LM Studio、模型 ID 与 Qdrant 状态。") from exc


@app.post("/api/ingest-local", response_model=IngestResponse)
async def ingest_local(request: LocalIngestRequest):
    raw_dir = (DATA / "raw").resolve()
    path = (raw_dir / request.filename).resolve()
    if path.parent != raw_dir or path.suffix.lower() != ".csv" or not path.exists():
        raise HTTPException(status_code=400, detail="离线摄取只允许读取 data/raw 下已存在的 CSV 文件。")
    try:
        if request.source_kind == "cfpb_mirror":
            complaints = load_cfpb_mirror_csv(str(path), request.limit, request.year, request.product_filter)
            ingest_year: int | str = request.year if request.year is not None else "all"
        else:
            complaints = load_credit_card_complaints_csv(str(path), request.limit, request.year or 2024)
            ingest_year = request.year or 2024
        guidance, guidance_failures = await fetch_official_guidance()
        return await _complete_ingest(complaints, guidance, guidance_failures, request.limit, ingest_year)
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RerankerUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("local ingest failed")
        raise HTTPException(status_code=503, detail="离线导入失败：请检查 CSV 字段、官方指导来源和模型/Qdrant 状态。") from exc


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    trace_id = app.state.rag.new_trace_id()
    try:
        answer, sources, citation_valid, invalid_citations, trace, quality = await app.state.rag.answer(request.question, request.top_k, retrieval_mode=request.retrieval_mode, assembly_version=request.assembly_version)
        try:
            trace_persistence = await app.state.storage.persist_trace(trace_id, trace)
        except Exception as trace_error:
            logger.warning("trace persistence skipped: %s", trace_error)
            trace_persistence = {"status": "failed", "reason": "trace_persistence_error"}
        return QueryResponse(
            answer=answer,
            sources=sources,
            guardrail="官方指导用于一般流程信息；投诉案例只是未经 CFPB 核实的消费者主张。系统不构成法律、金融或账户处理决定。",
            trace_id=trace_id,
            assembly_version=request.assembly_version,
            citation_valid=citation_valid,
            invalid_citations=invalid_citations,
            citation_coverage=float(quality.get("citation_coverage", 0.0)),
            safety_flags=list(quality.get("safety_flags", [])),
            needs_human_review=bool(quality.get("needs_human_review", False)),
            trace_persistence=trace_persistence,
            trace=trace,
        )
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RerankerUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("query failed")
        raise HTTPException(status_code=503, detail="查询失败：请确认 LM Studio、Qdrant、已导入数据和模型配置均已就绪。") from exc


@app.post("/api/retrieve-preview", response_model=RetrievalPreviewResponse)
async def retrieve_preview(request: QueryRequest):
    trace_id = app.state.rag.new_trace_id()
    trace = []
    started = app.state.rag.clock()
    app.state.rag.add_trace(trace, "query_received", started, "接收检索预览问题", {"question_chars": len(request.question), "top_k": request.top_k or 3, "retrieval_mode": request.retrieval_mode, "assembly_version": request.assembly_version, "generation": False})
    try:
        sources = await app.state.rag.retrieve(request.question, request.top_k, trace, request.retrieval_mode, assembly_version=request.assembly_version)
        app.state.rag.add_trace(trace, "preview_completed", started, "检索预览完成，未调用 Chat LLM", {"source_count": len(sources), "generation": False})
        try:
            await app.state.storage.persist_trace(trace_id, trace)
        except Exception as trace_error:
            logger.warning("preview trace persistence skipped: %s", trace_error)
        return RetrievalPreviewResponse(question=request.question, retrieval_mode=request.retrieval_mode, assembly_version=request.assembly_version, sources=sources, trace_id=trace_id, trace=trace)
    except DependencyNotReady as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except RerankerUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("retrieval preview failed")
        raise HTTPException(status_code=503, detail="检索预览失败：请确认 LM Studio Embedding、Qdrant 和索引均已就绪。") from exc


@app.post("/api/retrieve-stream")
async def retrieve_stream(request: QueryRequest):
    """Stream running/completed retrieval stages for the interactive workbench."""
    trace_id = app.state.rag.new_trace_id()

    async def event_stream():
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        trace = [
            TraceEvent(
                step=1,
                name="query_received",
                status="completed",
                duration_ms=0.0,
                summary="接收并准备检索问题",
                details={"question_chars": len(request.question), "retrieval_mode": request.retrieval_mode, "assembly_version": request.assembly_version},
            )
        ]

        def callback(event):
            queue.put_nowait({"type": "trace", "event": event.model_dump(mode="json")})

        yield json.dumps({"type": "meta", "trace_id": trace_id, "retrieval_mode": request.retrieval_mode, "assembly_version": request.assembly_version}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "trace", "event": trace[0].model_dump(mode="json")}, ensure_ascii=False) + "\n"
        task = asyncio.create_task(app.state.rag.retrieve(request.question, request.top_k, trace, request.retrieval_mode, callback, request.assembly_version))
        try:
            while not task.done() or not queue.empty():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield json.dumps(item, ensure_ascii=False) + "\n"
                except asyncio.TimeoutError:
                    continue
            sources = await task
            yield json.dumps(
                {"type": "result", "question": request.question, "retrieval_mode": request.retrieval_mode, "assembly_version": request.assembly_version, "trace_id": trace_id, "sources": [source.model_dump(mode="json") for source in sources], "trace": [event.model_dump(mode="json") for event in trace]},
                ensure_ascii=False,
            ) + "\n"
        except (DependencyNotReady, RerankerUnavailable) as exc:
            logger.warning("retrieval stream dependency unavailable: %s", exc)
            if not task.done():
                task.cancel()
            yield json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False) + "\n"
        except Exception as exc:
            logger.exception("retrieval stream failed")
            if not task.done():
                task.cancel()
            yield json.dumps({"type": "error", "detail": "检索流失败：请确认 LM Studio Embedding、Qdrant 和索引均已就绪。"}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
