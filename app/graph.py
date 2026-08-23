"""Optional structured GraphRAG store for V0.7 Support Intelligence.

Only fields already present in CFPB records are written as relationships. No
LLM is allowed to invent an entity or legal relationship here.
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    from neo4j import GraphDatabase
except ModuleNotFoundError:  # pragma: no cover
    GraphDatabase = None  # type: ignore[assignment,misc]


class GraphStore:
    def __init__(self, settings: Any):
        self.settings = settings
        self.enabled = bool(settings.graph_enabled)
        self.driver = None
        if self.enabled and GraphDatabase is not None:
            self.driver = GraphDatabase.driver(settings.neo4j_url, auth=(settings.neo4j_user, settings.neo4j_password))

    def status(self) -> dict[str, object]:
        if not self.enabled:
            return {"enabled": False, "state": "locked", "reason": "GRAPH_ENABLED=false"}
        if GraphDatabase is None:
            return {"enabled": True, "state": "not_installed", "reason": "安装 requirements-production.txt"}
        return {"enabled": True, "state": "configured", "url": self.settings.neo4j_url}

    async def health(self) -> dict[str, object]:
        status = self.status()
        if self.driver is None:
            return status
        try:
            await asyncio.to_thread(self.driver.verify_connectivity)
            status["state"] = "ready"
        except Exception as exc:
            status.update({"state": "offline", "error": str(exc)})
        return status

    def _build_sync(self, records: list[dict[str, Any]]) -> dict[str, int]:
        if self.driver is None:
            raise RuntimeError("Neo4j Graph profile 未启用或驱动未安装。")
        complaints = []
        sources = []
        relation_rows: dict[str, list[dict[str, str]]] = {
            "Product": [],
            "Issue": [],
            "Company": [],
            "Response": [],
        }
        relation_specs = (("product", "Product", "HAS_PRODUCT"), ("issue", "Issue", "HAS_ISSUE"), ("company", "Company", "INVOLVES_COMPANY"), ("company_response", "Response", "HAS_RESPONSE"))
        guidance_count = 0
        for payload in records:
            source_type = payload.get("source_type")
            metadata = payload.get("metadata") or {}
            source_url = str(payload.get("source_url", ""))
            title = str(payload.get("title", ""))
            sources.append({"url": source_url, "title": title, "source_type": str(source_type or "unknown")})
            if source_type == "complaint":
                complaint_id = str(payload.get("complaint_id") or payload.get("chunk_id"))
                complaints.append({"id": complaint_id, "url": source_url, "title": title})
                for key, label, _rel in relation_specs:
                    value = metadata.get(key)
                    if value:
                        relation_rows[label].append({"id": complaint_id, "value": str(value)})
            elif source_type in {"guidance", "regulation"}:
                guidance_count += 1
        counts = {
            "complaints": len(complaints),
            "guidance": guidance_count,
            "relationships": sum(len(rows) for rows in relation_rows.values()),
        }
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT complaint_id IF NOT EXISTS FOR (n:Complaint) REQUIRE n.complaint_id IS UNIQUE")
            session.run("CREATE CONSTRAINT source_url IF NOT EXISTS FOR (n:Source) REQUIRE n.url IS UNIQUE")
            session.run(
                """UNWIND $rows AS row
                MERGE (s:Source {url:row.url})
                SET s.title=row.title, s.source_type=row.source_type""",
                rows=sources,
            )
            session.run(
                """UNWIND $rows AS row
                MERGE (c:Complaint {complaint_id:row.id})
                SET c.source_url=row.url, c.title=row.title
                MERGE (s:Source {url:row.url})
                SET s.title=row.title, s.source_type='complaint'
                MERGE (c)-[:FROM_SOURCE]->(s)""",
                rows=complaints,
            )
            for label, rows in relation_rows.items():
                if not rows:
                    continue
                rel = next(spec[2] for spec in relation_specs if spec[1] == label)
                session.run(
                    f"""UNWIND $rows AS row
                    MATCH (c:Complaint {{complaint_id:row.id}})
                    MERGE (n:{label} {{name:row.value}})
                    MERGE (c)-[:{rel}]->(n)""",
                    rows=rows,
                )
        return counts

    async def build_from_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("V0.7 Graph profile 当前锁定；先完成纯文本 RAG 质量门。")
        return await asyncio.to_thread(self._build_sync, records)

    def _query_sync(self, query_kind: str, limit: int) -> list[dict[str, Any]]:
        if self.driver is None:
            raise RuntimeError("Neo4j Graph profile 未就绪。")
        queries = {
            "top_issues": """MATCH (i:Issue)<-[:HAS_ISSUE]-(c:Complaint)
                RETURN i.name AS issue, count(c) AS complaint_count
                ORDER BY complaint_count DESC LIMIT $limit""",
            "top_products": """MATCH (p:Product)<-[:HAS_PRODUCT]-(c:Complaint)
                RETURN p.name AS product, count(c) AS complaint_count
                ORDER BY complaint_count DESC LIMIT $limit""",
        }
        if query_kind not in queries:
            raise ValueError("只允许 top_issues 或 top_products 图查询。")
        with self.driver.session() as session:
            return [dict(record) for record in session.run(queries[query_kind], limit=limit)]

    async def query(self, query_kind: str, limit: int = 10) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._query_sync, query_kind, max(1, min(limit, 50)))

    async def close(self) -> None:
        if self.driver is not None:
            await asyncio.to_thread(self.driver.close)
