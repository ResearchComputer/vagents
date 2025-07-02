import os
import json
import backoff
import aiohttp
from pydantic import BaseModel
from typing import (
    Optional,
    Callable,
    List,
    Tuple,
    AsyncGenerator,
    Union,
    Dict,
)
import logging
from vagents.utils import logger

from .protocol import Message

backoff_logger = logging.getLogger("backoff")

VAGENT_MAX_BACKOFF_TIME = int(os.environ.get("VAGENT_MAX_BACKOFF_TIME", 5 * 60))


class LLM:
    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        # Adding default_model attribute to avoid KeyError
        self.default_model = model_name
        # Create a shared session with higher connection limits
        self._session = None

    async def _get_session(self):
        """Get or create a shared aiohttp session with optimized connection limits."""
        if self._session is None or self._session.closed:
            # Create connector with higher connection limits
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=50,  # Max connections per host
                keepalive_timeout=60,  # Keep connections alive longer
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=600)
            )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _prepare_input(
        self,
        messages: List[Union[Message, Dict]],
        tools: Optional[List[Callable]],
        response_format: Optional[BaseModel] = None,
    ):
        if isinstance(messages[0], dict):
            messages = [Message(role=m["role"], content=m["content"]) for m in messages]
        if response_format and hasattr(response_format, "model_json_schema"):
            return_type = {
                "type": "json_schema",
                "json_schema": {
                    "name": "foo",
                    "schema": response_format.model_json_schema(),
                },
            }
            return messages, None, return_type
        elif tools:
            return messages, tools, None
        else:
            return messages, None, None

    def _prepare_payload(
        self,
        messages: List[Union[Message, Dict]],
        temperature: Optional[float] = 0.3,
        max_tokens: Optional[int] = None,
        min_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[Callable]] = None,
        response_format: Optional[BaseModel] = None,
        stream: Optional[bool] = False,
    ) -> Tuple[bool, dict]:
        messages, tools, return_format = self._prepare_input(
            messages, tools, response_format
        )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.default_model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "min_tokens": min_tokens,
            "response_format": return_format,
            "stream": False if tools else stream,
            "tools": tools,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "top_p": 1.0,
        }
        # remove None values
        for key in list(payload.keys()):
            if payload[key] is None:
                del payload[key]
        return endpoint, headers, payload

    @backoff.on_exception(
        backoff.expo,
        aiohttp.ClientError,
        max_time=VAGENT_MAX_BACKOFF_TIME,
        logger="backoff",
    )
    async def _async_call_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = 0.3,
        max_tokens: Optional[int] = None,
        min_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[Callable]] = None,
        response_format: Optional[BaseModel] = None,
        stream: Optional[bool] = False,
    ) -> AsyncGenerator[str, None]:
        endpoint, headers, payload = self._prepare_payload(
            messages,
            temperature,
            max_tokens,
            min_tokens,
            model,
            tools,
            response_format,
            stream=stream,
        )

        session = await self._get_session()
        async with session.post(endpoint, json=payload, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise aiohttp.ClientError(f"Request failed [{resp.status}]: {text}")
            if stream:
                try:
                    async for chunk in resp.content:
                        chunk = chunk.decode().replace("data: ", "").strip()
                        if not chunk:
                            continue
                        if chunk == "[DONE]":
                            return
                        chunk = json.loads(chunk)
                        if "choices" not in chunk:
                            continue
                        chunk = chunk["choices"]
                        if len(chunk) == 0:
                            continue
                        chunk = chunk[0]["delta"]["content"]
                        if chunk:
                            yield chunk
                except aiohttp.client_exceptions.ClientPayloadError as e:
                    logger.error(f"Streaming payload error: {e}")
                    # Stop streaming on payload errors
                    return
            else:
                result = await resp.json()
                if tools:
                    result = result["choices"][0]["message"]["tool_calls"]
                else:
                    if result["choices"][0]["message"]["content"] is None:
                        result = result["choices"][0]["message"]["reasoning_content"]
                    else:
                        result = result["choices"][0]["message"]["content"]
                yield result

    def _post_process(
        self,
        result: str,
        tools: Optional[List[Callable]],
        response_format: Optional[BaseModel],
    ):
        if response_format and hasattr(response_format, "model_validate"):
            validated_result = response_format.model_validate(json.loads(result))
            return validated_result
        elif tools:
            result = json.loads(result)
            return result
        return result

    async def __call__(
        self,
        messages: List[Union[Message, Dict]],
        temperature: Optional[float] = 0.1,
        max_tokens: Optional[int] = None,
        min_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[Callable]] = None,
        response_format: Optional[BaseModel] = None,
        stream: Optional[bool] = False,
    ):
        if tools and stream:
            stream = False
            logger.warning(
                "Streaming is not supported with tools. Disabling streaming."
            )
        # For non-streaming calls, consume the generator to close the session context
        gen = self._async_call_chat(
            messages,
            temperature,
            max_tokens,
            min_tokens,
            model,
            tools,
            response_format,
            stream=stream,
        )

        if not stream and not tools:
            result = None
            async for chunk in gen:
                result = chunk
            return result
        return gen
