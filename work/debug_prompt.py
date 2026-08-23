import asyncio
import httpx

from app.config import get_settings
from app.rag import RagService
from app.schemas import SourceHit


async def main() -> None:
    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.post(
            "http://localhost:18000/api/retrieve-preview",
            json={"question": "我发现信用卡有一笔陌生扣款，客服应该先确认哪些信息？", "retrieval_mode": "dense"},
        )
        payload = response.json()
    sources = [SourceHit.model_validate(item) for item in payload["sources"]]
    service = RagService(get_settings())
    prompt = service.build_prompt("我发现信用卡有一笔陌生扣款，客服应该先确认哪些信息？", sources, service.settings.max_context_chars)
    print({"settings": service.settings.model_dump(), "prompt_chars": len(prompt), "prompt_tokens_estimate": len(prompt) // 4, "sources": len(sources)})
    await service.close()


asyncio.run(main())
