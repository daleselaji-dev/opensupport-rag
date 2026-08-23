"""PostgreSQL/MinIO source-of-truth adapter for the production profile.

The local learner path can run without these services. When the core Compose
profile is enabled, each successful ingestion persists a normalized snapshot,
document versions, chunks and index membership before exposing the result as
an active production snapshot.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date, datetime
from io import BytesIO
from typing import Any, Sequence
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.config import Settings
from app.data_foundation import canonical_url
from app.schemas import DataQualityReport, SourceDocument

try:  # Optional until the production profile is installed.
    import psycopg
except ModuleNotFoundError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]

try:  # Optional until the production profile is installed.
    from minio import Minio
except ModuleNotFoundError:  # pragma: no cover
    Minio = None  # type: ignore[assignment,misc]

try:  # Optional until the production profile is installed.
    import redis.asyncio as redis_async
except ModuleNotFoundError:  # pragma: no cover
    redis_async = None  # type: ignore[assignment]


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(value[:10]), datetime.min.time())
        except ValueError:
            return None


class SourceOfTruthStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._health_cache: dict[str, str] | None = None
        self._health_cache_at = 0.0

    @property
    def required(self) -> bool:
        return bool(getattr(self.settings, "truth_source_required", False))

    @property
    def postgres_dsn(self) -> str:
        return self.settings.postgres_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def _minio_client(self):
        if Minio is None:
            raise RuntimeError("MinIO 客户端未安装，请安装 requirements-production.txt。")
        return Minio(
            self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=False,
        )

    def _postgres_ping_sync(self) -> None:
        if psycopg is None:
            raise RuntimeError("PostgreSQL 驱动未安装")
        with psycopg.connect(self.postgres_dsn, connect_timeout=1) as conn:
            conn.execute("SELECT 1")

    async def health(self) -> dict[str, str]:
        if not self.settings.storage_probe_enabled:
            return {"postgres": "not_probed", "minio": "not_probed", "redis": "not_probed"}
        if self._health_cache is not None and time.monotonic() - self._health_cache_at < 5:
            return dict(self._health_cache)
        statuses = {"postgres": "not_installed", "minio": "not_installed", "redis": "not_installed"}
        if psycopg is not None:
            try:
                await asyncio.to_thread(self._postgres_ping_sync)
                statuses["postgres"] = "ready"
            except Exception:
                statuses["postgres"] = "offline"
        if Minio is not None:
            try:
                client = self._minio_client()
                await asyncio.wait_for(asyncio.to_thread(client.bucket_exists, self.settings.minio_bucket), timeout=1.5)
                statuses["minio"] = "ready"
            except Exception:
                statuses["minio"] = "offline"
        if redis_async is not None:
            client = redis_async.from_url(self.settings.redis_url, socket_connect_timeout=2)
            try:
                await asyncio.wait_for(client.ping(), timeout=1.5)
                statuses["redis"] = "ready"
            except Exception:
                statuses["redis"] = "offline"
            finally:
                await client.aclose()
        self._health_cache = dict(statuses)
        self._health_cache_at = time.monotonic()
        return statuses

    async def _put_snapshot(self, snapshot_id: str, documents: Sequence[SourceDocument]) -> str:
        client = self._minio_client()
        bucket = self.settings.minio_bucket
        exists = await asyncio.to_thread(client.bucket_exists, bucket)
        if not exists:
            await asyncio.to_thread(client.make_bucket, bucket)
        payload = {
            "snapshot_id": snapshot_id,
            "artifact_type": "normalized_source_snapshot",
            "documents": [document.model_dump(mode="json") for document in documents],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        object_key = f"snapshots/{snapshot_id}/normalized_documents.json"
        await asyncio.to_thread(
            client.put_object,
            bucket,
            object_key,
            BytesIO(body),
            len(body),
            "application/json; charset=utf-8",
        )
        return object_key

    def _persist_postgres_sync(
        self,
        job_id: str,
        started: datetime,
        documents: Sequence[SourceDocument],
        quality: DataQualityReport,
        indexed_documents: int,
        collection_name: str,
        embedding_model: str,
        raw_object_key: str,
    ) -> str:
        index_version = f"{quality.snapshot_id}-{collection_name}"
        with psycopg.connect(self.postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO ingestion_jobs
                    (job_id, requested_limit, status, snapshot_id, accepted_documents,
                     duplicate_documents, quarantined_documents, indexed_documents,
                     started_at, finished_at)
                    VALUES (%s, %s, 'active', %s, %s, %s, %s, %s, %s, %s)""",
                    (job_id, quality.raw_documents, quality.snapshot_id, quality.accepted_documents,
                     quality.duplicate_documents, quality.quarantined_documents, indexed_documents,
                     started, datetime.now().astimezone()),
                )
                cur.execute(
                    """INSERT INTO index_versions
                    (index_version, snapshot_id, collection_name, embedding_model, status, activated_at)
                    VALUES (%s, %s, %s, %s, 'active', %s)
                    ON CONFLICT (index_version) DO UPDATE SET status='active', activated_at=EXCLUDED.activated_at""",
                    (index_version, quality.snapshot_id, collection_name, embedding_model, datetime.now().astimezone()),
                )
                for order, document in enumerate(documents):
                    external_id = document.complaint_id or document.chunk_id
                    source_key = canonical_url(document.source_url)
                    if document.source_type == "complaint":
                        source_key = f"{source_key}:complaint:{external_id}"
                    cur.execute(
                        """INSERT INTO source_documents
                        (source_url, source_type, external_id, title, canonical_url)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (source_type, canonical_url) DO UPDATE SET title=EXCLUDED.title
                        RETURNING id""",
                        (document.source_url, document.source_type, external_id, document.title, source_key),
                    )
                    source_row = cur.fetchone()
                    if source_row is None:
                        raise RuntimeError(f"无法创建 source_documents：{document.chunk_id}")
                    cur.execute(
                        """INSERT INTO document_versions
                        (document_id, content_sha256, raw_object_key, published_at, lifecycle_status, parser_name, parser_version, metadata)
                        VALUES (%s, %s, %s, %s, 'active', 'opensupport-normalizer', %s, %s::jsonb)
                        ON CONFLICT (document_id, content_sha256) DO UPDATE SET lifecycle_status='active'
                        RETURNING id""",
                        (source_row[0], document.metadata.get("content_sha256", ""), raw_object_key,
                         _parse_timestamp(document.published_at), quality.pipeline_version,
                         json.dumps(document.metadata, ensure_ascii=False)),
                    )
                    version_row = cur.fetchone()
                    if version_row is None:
                        raise RuntimeError(f"无法创建 document_versions：{document.chunk_id}")
                    cur.execute(
                        """INSERT INTO chunks
                        (chunk_id, document_version_id, chunk_order, text, normalized_text_sha256, language, metadata, lifecycle_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, 'active')
                        ON CONFLICT (chunk_id) DO UPDATE SET text=EXCLUDED.text, metadata=EXCLUDED.metadata, lifecycle_status='active'""",
                        (document.chunk_id, version_row[0], order, document.text,
                         document.metadata.get("normalized_text_sha256", ""), document.metadata.get("language"),
                         json.dumps(document.metadata, ensure_ascii=False)),
                    )
                    point_id = str(uuid5(NAMESPACE_URL, f"opensupport:{document.chunk_id}"))
                    cur.execute(
                        """INSERT INTO index_memberships (index_version, chunk_id, qdrant_point_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (index_version, chunk_id) DO UPDATE SET qdrant_point_id=EXCLUDED.qdrant_point_id""",
                        (index_version, document.chunk_id, point_id),
                    )
            conn.commit()
        return index_version

    async def persist_ingestion(
        self,
        documents: Sequence[SourceDocument],
        quality: DataQualityReport,
        indexed_documents: int,
        collection_name: str,
        embedding_model: str,
    ) -> dict[str, Any]:
        """Persist one normalized snapshot and its derived index membership."""

        started = datetime.now().astimezone()
        job_id = str(uuid4())
        statuses = await self.health()
        missing = [name for name in ("postgres", "minio") if statuses.get(name) != "ready"]
        if missing:
            result = {
                "status": "required_unavailable" if self.required else "skipped",
                "job_id": job_id,
                "missing": missing,
                "message": "PostgreSQL/MinIO 未就绪；本地模式保留 JSON 质量报告，生产模式必须启动 core profile。",
            }
            if self.required:
                raise RuntimeError(result["message"])
            return result

        if psycopg is None:
            raise RuntimeError("PostgreSQL 驱动未安装，请安装 requirements-production.txt。")

        raw_object_key = await self._put_snapshot(quality.snapshot_id, documents)
        index_version = await asyncio.to_thread(
            self._persist_postgres_sync,
            job_id,
            started,
            documents,
            quality,
            indexed_documents,
            collection_name,
            embedding_model,
            raw_object_key,
        )
        return {
            "status": "persisted",
            "job_id": job_id,
            "snapshot_id": quality.snapshot_id,
            "index_version": index_version,
            "raw_object_key": raw_object_key,
            "started_at": started.isoformat(),
        }

    def _persist_trace_sync(self, trace_id: str, events: Sequence[Any]) -> None:
        with psycopg.connect(self.postgres_dsn) as conn:
            with conn.cursor() as cur:
                for event in events:
                    span_id = f"{event.step}:{event.name}"
                    cur.execute(
                        """INSERT INTO trace_spans
                        (trace_id, span_id, parent_span_id, component, status, duration_ms, details)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (trace_id, span_id) DO UPDATE SET status=EXCLUDED.status, duration_ms=EXCLUDED.duration_ms, details=EXCLUDED.details""",
                        (trace_id, span_id, None, event.name, event.status, event.duration_ms, json.dumps(event.details, ensure_ascii=False)),
                    )
            conn.commit()

    async def persist_trace(self, trace_id: str, events: Sequence[Any]) -> dict[str, Any]:
        if not self.settings.trace_persistence_enabled or not events:
            return {"status": "disabled", "trace_id": trace_id}
        statuses = await self.health()
        if statuses.get("postgres") != "ready":
            return {"status": "skipped", "trace_id": trace_id, "reason": "postgres_unavailable"}
        await asyncio.to_thread(self._persist_trace_sync, trace_id, events)
        return {"status": "persisted", "trace_id": trace_id, "span_count": len(events)}

    def _persist_agent_draft_sync(self, draft_id: str, trace_id: str, payload: dict[str, Any]) -> None:
        with psycopg.connect(self.postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO agent_drafts (draft_id, trace_id, status, payload)
                    VALUES (%s, %s, 'pending_approval', %s::jsonb)
                    ON CONFLICT (draft_id) DO NOTHING""",
                    (draft_id, trace_id, json.dumps(payload, ensure_ascii=False)),
                )
            conn.commit()

    async def persist_agent_draft(self, draft_id: str, trace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        statuses = await self.health()
        if statuses.get("postgres") != "ready":
            if self.required:
                raise RuntimeError("Agent 草稿需要 PostgreSQL 才能进入待审批队列。")
            return {"status": "skipped", "reason": "postgres_unavailable", "draft_id": draft_id}
        await asyncio.to_thread(self._persist_agent_draft_sync, draft_id, trace_id, payload)
        return {"status": "persisted", "draft_id": draft_id}

    def _approve_agent_draft_sync(self, draft_id: str, approved_by: str) -> bool:
        with psycopg.connect(self.postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE agent_drafts
                    SET status='approved', approved_by=%s, approved_at=now()
                    WHERE draft_id=%s AND status='pending_approval'""",
                    (approved_by, draft_id),
                )
                changed = cur.rowcount == 1
            conn.commit()
        return changed

    async def approve_agent_draft(self, draft_id: str, approved_by: str) -> dict[str, Any]:
        statuses = await self.health()
        if statuses.get("postgres") != "ready":
            raise RuntimeError("人工审批需要 PostgreSQL 待审批队列可用。")
        approved = await asyncio.to_thread(self._approve_agent_draft_sync, draft_id, approved_by)
        return {"status": "approved" if approved else "not_pending", "draft_id": draft_id, "approved_by": approved_by}
