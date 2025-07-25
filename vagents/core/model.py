import os
import asyncio
import aiohttp
from vagents.core.executor import get_executor

from typing import Callable

llm_allowed_kwargs = (
    "messages",
    "temperature",
    "top_p",
    "max_tokens",
    "stream",
    "stop",
    "n",
    "presence_penalty",
    "frequency_penalty",
)


class LM:
    def __init__(
        self,
        name: str,
        base_url: str = os.environ.get("VAGENTS_LM_BASE_URL", "http://localhost:8000"),
        api_key: str = os.environ.get("VAGENTS_LM_API_KEY", "your-api-key-here"),
    ):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "vagents/1.0",
        }
        self._executor = get_executor()

    def __call__(self, *args, **kwargs) -> asyncio.Future:
        task = asyncio.create_task(self._request(*args, **kwargs))
        return self._executor.enqueue(task)

    async def invoke(self, func: Callable, *args, **kwargs) -> asyncio.Future:
        messages = func(*args, **kwargs)
        kwargs = {k: v for k, v in kwargs.items() if k in llm_allowed_kwargs}
        return await self(messages=messages, **kwargs)

    # -- Below are internal apis that are not meant to be used directly --
    async def _request(self, *args, **kwargs):
        data = {"model": self.name, **kwargs}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions", headers=self._headers, json=data
            ) as response:
                if response.status != 200:
                    raise Exception(f"Request failed with status {response.status}")
                return await response.json()


if __name__ == "__main__":
    lm = LM(name="Qwen/Qwen3-32B")

    async def main():
        # Option 1: Start all requests concurrently, then wait for all
        future1 = lm(
            messages=[{"role": "user", "content": "Hello, how are you? in one word"}]
        )
        future2 = lm(
            messages=[
                {"role": "user", "content": "Hello, how are you doing? in one word"}
            ]
        )
        future3 = lm(
            messages=[
                {"role": "user", "content": "Hello, who is alan turing? in one word"}
            ]
        )
        tasks = [future1, future2, future3]
        # Wait for all to complete
        response1, response2, response3 = await asyncio.gather(*tasks)
        print("Response 1:", response1)
        print("Response 2:", response2)
        print("Response 3:", response3)

    asyncio.run(main())
