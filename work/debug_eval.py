import asyncio
import traceback

from app.config import get_settings
from app.eval import run_retrieval_eval
from app.rag import RagService


async def main() -> None:
    rag = RagService(get_settings())
    try:
        print(await rag.index_inventory())
        result = await run_retrieval_eval(rag)
        print(result.model_dump())
    except Exception:
        traceback.print_exc()
    finally:
        await rag.close()


asyncio.run(main())
