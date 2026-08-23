"""Atomic local blue/green index alias registry.

The JSON pointer is a small local control-plane artifact; PostgreSQL keeps the
durable index_versions/index_memberships lineage. Switching the pointer never
deletes a collection, so rollback is reversible.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings


class IndexAliasRegistry:
    def __init__(self, settings: Settings):
        self.path = Path(settings.data_dir) / "index_alias.json"
        self.settings = settings

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "active_collection": self.settings.collection_name,
                "active_sparse_collection": self.settings.sparse_collection_name,
                "previous": [],
                "status": "implicit_default",
            }
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "active_collection": self.settings.collection_name,
                "active_sparse_collection": self.settings.sparse_collection_name,
                "previous": [],
                "status": "corrupt_fallback_default",
            }

    def active(self) -> tuple[str, str]:
        payload = self.read()
        return str(payload["active_collection"]), str(payload["active_sparse_collection"])

    def activate(self, collection: str, sparse_collection: str, *, reason: str) -> dict[str, Any]:
        current = self.read()
        previous = list(current.get("previous", []))
        previous.insert(0, {"active_collection": current["active_collection"], "active_sparse_collection": current["active_sparse_collection"], "at": datetime.now(timezone.utc).isoformat(), "reason": reason})
        payload = {
            "active_collection": collection,
            "active_sparse_collection": sparse_collection,
            "previous": previous[:10],
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "status": "active",
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, self.path)
        return payload

    def rollback(self) -> dict[str, Any]:
        current = self.read()
        previous = list(current.get("previous", []))
        if not previous:
            raise RuntimeError("没有可回滚的上一版索引 Alias。")
        target = previous.pop(0)
        payload = {
            "active_collection": target["active_collection"],
            "active_sparse_collection": target["active_sparse_collection"],
            "previous": previous,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "reason": "manual_rollback",
            "status": "rolled_back",
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, self.path)
        return payload
