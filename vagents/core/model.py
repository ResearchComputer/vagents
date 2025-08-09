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
        base_url: str = os.environ.get(
            "VAGENTS_LM_BASE_URL", "https://ai.research.computer"
        ),
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
        # Only pass positional args to the template/message builder to avoid
        # leaking LLM invocation kwargs (like temperature) or unrelated kwargs
        # into user-provided functions.
        messages = func(*args)
        lm_kwargs = {k: v for k, v in kwargs.items() if k in llm_allowed_kwargs}
        return await self(messages=messages, **lm_kwargs)

    # -- Below are internal apis that are not meant to be used directly --
    async def _request(self, *args, **kwargs):
        # Fast-path for tests/offline runs to avoid network calls
        offline = os.environ.get("VAGENTS_LM_FAKE", "").lower() in {"1", "true", "yes"}
        if offline:
            messages = kwargs.get("messages") or []
            try:
                # Try to extract last user content for a deterministic fake response
                last_user = next(
                    (
                        m
                        for m in reversed(messages)
                        if isinstance(m, dict) and m.get("role") == "user"
                    ),
                    None,
                )
                content = (
                    last_user.get("content", "") if isinstance(last_user, dict) else ""
                )
                if isinstance(content, list):
                    # For multimodal messages, concatenate text parts
                    content = "\n".join(
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    )
                snippet = (content or "").strip()
            except Exception:
                snippet = ""
            return {
                "choices": [
                    {
                        "message": {
                            "content": f"[FAKE:{self.name}] "
                            + (snippet[:200] if snippet else "OK")
                        }
                    }
                ]
            }

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
