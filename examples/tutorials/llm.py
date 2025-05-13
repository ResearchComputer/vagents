import os
import asyncio
from vagents.core import LLM

llm = LLM(
    model_name="meta-llama/Llama-3.3-70B-Instruct",
    base_url=os.environ.get("RC_API_BASE", ""),
    api_key=os.environ.get("RC_API_KEY", ""),
)


async def main():
    result = await llm([{"role": "user", "content": "What is the capital of France?"}])
    print(await result.__anext__())


asyncio.run(main())
