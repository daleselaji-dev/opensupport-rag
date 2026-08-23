"""Optional V0.4 cross-encoder reranking.

The retriever and the reranker solve different problems.  Dense/BM25/RRF
produce a reasonably high-recall candidate set; a cross-encoder reads the
question and each candidate together and estimates pairwise relevance.  It is
therefore deliberately lazy, bounded to the candidate set, and never used as
the first-stage full-corpus searcher.

The dependency is optional so the V0.1--V0.3 learning path stays lightweight.
V0.4 exposes an actionable 424 error until the operator installs the optional
package and enables the model explicitly.
"""

from __future__ import annotations

from typing import Any, Sequence

import httpx

from app.config import Settings


class RerankerUnavailable(RuntimeError):
    """The optional reranker is not installed/configured."""


class CrossEncoderReranker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model: Any | None = None
        self._load_error: str | None = None

    def status(self) -> dict[str, object]:
        if not self.settings.reranker_enabled:
            return {
                "enabled": False,
                "available": False,
                "state": "disabled",
                "model": self.settings.reranker_model,
                "install": "设置 RERANKER_ENABLED=true 后，安装 requirements-reranker.txt",
            }
        if self.settings.reranker_provider.lower() in {"llama_cpp", "remote"}:
            return {
                "enabled": True,
                "available": True,
                "state": "remote_configured",
                "provider": self.settings.reranker_provider,
                "base_url": self.settings.reranker_base_url,
                "model": self.settings.reranker_model,
            }
        if self._model is not None:
            return {"enabled": True, "available": True, "state": "ready", "model": self.settings.reranker_model}
        if self._load_error:
            return {
                "enabled": True,
                "available": False,
                "state": "unavailable",
                "model": self.settings.reranker_model,
                "error": self._load_error,
                "install": "安装 requirements-reranker.txt；首次运行会从 Hugging Face 下载模型。",
            }
        return {
            "enabled": True,
            "available": False,
            "state": "not_loaded",
            "model": self.settings.reranker_model,
            "install": "安装 requirements-reranker.txt；首次运行会从 Hugging Face 下载模型。",
        }

    async def health(self) -> dict[str, object]:
        status = self.status()
        if not self.settings.reranker_enabled or self.settings.reranker_provider.lower() not in {"llama_cpp", "remote"}:
            return status
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=1.0) as client:
                response = await client.get(f"{self.settings.reranker_base_url.rstrip('/')}/health")
                response.raise_for_status()
            status.update({"available": True, "state": "ready", "health_status": response.status_code})
        except Exception as exc:
            status.update({"available": False, "state": "offline", "error": str(exc)})
        return status

    def _load(self) -> Any:
        if not self.settings.reranker_enabled:
            raise RerankerUnavailable(
                "V0.4 Cross-Encoder 尚未启用。请设置 RERANKER_ENABLED=true，并安装 requirements-reranker.txt。"
            )
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.settings.reranker_model,
                device=self.settings.reranker_device,
                max_length=self.settings.reranker_max_length,
            )
        except Exception as exc:  # model download/import errors are operator errors
            self._load_error = str(exc)
            raise RerankerUnavailable(
                "V0.4 Cross-Encoder 不可用。请安装 requirements-reranker.txt，"
                f"检查模型 {self.settings.reranker_model} 是否可下载；原始原因：{exc}"
            ) from exc
        return self._model

    def rerank(self, question: str, hits: Sequence[Any], final_k: int) -> list[Any]:
        if not hits:
            return []
        if not self.settings.reranker_enabled:
            raise RerankerUnavailable(
                "V0.4 Cross-Encoder 默认关闭。请设置 RERANKER_ENABLED=true，并启动本地 Reranker 服务后再运行。"
            )
        if self.settings.reranker_provider.lower() in {"llama_cpp", "remote"}:
            return self._rerank_remote(question, hits, final_k)
        model = self._load()
        pairs = [(question, hit.text) for hit in hits]
        scores = model.predict(pairs, show_progress_bar=False)
        ranked = []
        for hit, score in zip(hits, scores, strict=True):
            metadata = dict(hit.metadata)
            metadata["retriever_score"] = hit.score
            metadata["rerank_score"] = round(float(score), 6)
            ranked.append(hit.model_copy(update={"score": round(float(score), 6), "metadata": metadata}))
        ranked.sort(key=lambda hit: hit.score, reverse=True)
        return ranked[:final_k]

    def _rerank_remote(self, question: str, hits: Sequence[Any], final_k: int) -> list[Any]:
        """Call llama.cpp's local `/reranking` endpoint.

        The endpoint returns original candidate indices plus relevance scores;
        this keeps the adapter independent from LM Studio's chat/embedding
        APIs and preserves the exact candidate-to-score mapping in Trace.
        """

        batch_size = max(1, self.settings.reranker_batch_size)
        text_limit = max(256, self.settings.reranker_text_chars)
        all_results: list[tuple[int, float]] = []
        for start in range(0, len(hits), batch_size):
            batch_hits = hits[start : start + batch_size]
            payload = {
                "model": self.settings.reranker_model,
                "query": question,
                "documents": [hit.text[:text_limit] for hit in batch_hits],
            }
            try:
                response = httpx.post(
                    f"{self.settings.reranker_base_url.rstrip('/')}/reranking",
                    json=payload,
                    timeout=self.settings.reranker_timeout_s,
                    trust_env=False,
                )
                response.raise_for_status()
                body = response.json()
                results = body.get("results", [])
            except Exception as exc:
                self._load_error = str(exc)
                raise RerankerUnavailable(
                    f"本地 Reranker 服务不可用：{self.settings.reranker_base_url}/reranking；"
                    "请启动 llama-server（--embedding --pooling rank --rerank）并确认模型已加载。"
                    f"原始原因：{exc}"
                ) from exc
            if not isinstance(results, list) or not results:
                raise RerankerUnavailable("本地 Reranker 返回空结果，未进行静默降级。")
            for item in results:
                try:
                    all_results.append((start + int(item["index"]), float(item["relevance_score"])))
                except (KeyError, TypeError, ValueError) as exc:
                    raise RerankerUnavailable("本地 Reranker 返回了无法映射到候选集的结果。") from exc
        ranked: list[Any] = []
        for index, score in all_results:
            try:
                hit = hits[index]
            except (IndexError, TypeError, ValueError) as exc:
                raise RerankerUnavailable("本地 Reranker 返回了无法映射到候选集的结果。") from exc
            metadata = dict(hit.metadata)
            metadata["retriever_score"] = hit.score
            metadata["rerank_score"] = round(score, 6)
            metadata["reranker_provider"] = self.settings.reranker_provider
            metadata["reranker_model"] = self.settings.reranker_model
            ranked.append(hit.model_copy(update={"score": round(score, 6), "metadata": metadata}))
        return ranked[:final_k]
