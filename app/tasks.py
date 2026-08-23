"""Small production-profile tasks; heavy ingestion is added incrementally."""

from __future__ import annotations

from datetime import datetime, timezone

from app.celery_app import celery_app

if celery_app is not None:

    @celery_app.task(name="opensupport.pipeline.healthcheck")
    def pipeline_healthcheck() -> dict[str, str]:
        return {"status": "ready", "checked_at": datetime.now(timezone.utc).isoformat()}

    @celery_app.task(name="opensupport.pipeline.build_contextual_index", bind=True)
    def build_contextual_index_task(self) -> dict[str, object]:
        """Run the V0.5 derived-index build outside the API request thread."""

        import asyncio

        from app.config import get_settings
        from app.rag import RagService

        async def run() -> dict[str, object]:
            rag = RagService(get_settings())
            try:
                return await rag.build_contextual_index()
            finally:
                await rag.close()

        return asyncio.run(run())

else:

    def pipeline_healthcheck() -> dict[str, str]:  # pragma: no cover - optional dependency guard
        raise RuntimeError("Celery 未安装；请安装 requirements-production.txt 后启动 worker。")
