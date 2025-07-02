import inspect
import asyncio
from copy import deepcopy
from vagents.core import LLM, Message, Tool, parse_function_signature
from typing import Callable, Union, List, Optional, Dict


class LMManager:
    def __init__(self, max_concurrent_requests: int = 10):
        self.models: Dict[str, LLM] = {}
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.request_queue = asyncio.Queue()
        self.active_requests = 0
        self._queue_processor_task = None

    def set_max_concurrency(self, max_concurrent_requests: int):
        """Update the maximum number of concurrent requests allowed."""
        self.max_concurrent_requests = max_concurrent_requests
        # Note: Creating a new semaphore will reset the current count
        # This means existing requests won't be affected, only new ones
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _process_queue(self):
        """Background task to process queued requests."""
        while True:
            try:
                # Get the next request from the queue
                request_data = await self.request_queue.get()
                if request_data is None:  # Shutdown signal
                    break

                # Start the request processing as a separate task
                asyncio.create_task(self._process_single_request(request_data))

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue processing
                print(f"Error in queue processor: {e}")

    async def _process_single_request(self, request_data):
        """Process a single request with concurrency control."""
        coro, future = request_data

        # Acquire semaphore to limit concurrency
        async with self.semaphore:
            self.active_requests += 1
            try:
                # Execute the request
                result = await coro
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
            finally:
                self.active_requests -= 1
                self.request_queue.task_done()

    def _ensure_queue_processor(self):
        """Ensure the queue processor task is running."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_queue())

    async def _enqueue_request(self, coro):
        """Add a request to the queue and return a future for the result."""
        self._ensure_queue_processor()
        future = asyncio.Future()
        await self.request_queue.put((coro, future))
        return await future

    async def shutdown(self):
        """Gracefully shutdown the manager."""
        # Signal queue processor to stop
        await self.request_queue.put(None)

        # Wait for current requests to complete
        if self._queue_processor_task:
            await self._queue_processor_task

        # Close all model sessions
        for model in self.models.values():
            if hasattr(model, "close"):
                await model.close()

    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status information."""
        return {
            "queue_size": self.request_queue.qsize(),
            "active_requests": self.active_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
        }

    def add_model(self, llm: LLM):
        self.models[llm.model_name] = llm

    async def call(self, model_name: str, *args, **kwargs):
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found.")

        # Create coroutine for the actual model call
        async def _model_call():
            return await self.models[model_name](*args, **kwargs)

        # Enqueue the request and wait for result
        return await self._enqueue_request(_model_call())

    async def invoke(
        self,
        func: Callable,
        model_name: str,
        query: Union[List[Message], str],
        tools: Optional[List[Union[Callable, Tool]]] = None,
        **kwargs,
    ):
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found.")

        # Create coroutine for the actual invoke operation
        async def _invoke_call():
            docstring = inspect.getdoc(func) or "You are a helpful assistant."
            response_format = func.__annotations__.get("return", None)

            messages = deepcopy(query)

            if isinstance(query, List):
                if query[0].role != "system":
                    messages.insert(0, Message(role="system", content=docstring))
                else:
                    messages[0].content = docstring
            elif isinstance(query, str):
                messages = [Message(role="system", content=docstring)]
            kwargs["tools"] = tools

            messages.append(Message(role="user", content=func(query, **kwargs)))
            tool_info = None
            if tools:
                tool_info = [
                    tool.to_llm_format()
                    if isinstance(tool, Tool)
                    else parse_function_signature(tool)
                    for tool in tools
                ]

            # remove kwargs that are not in the llm signature
            for key in list(kwargs.keys()):
                if key not in [
                    "messages",
                    "tools",
                    "response_format",
                    "temperature",
                    "max_tokens",
                    "min_tokens",
                    "model",
                    "tools",
                    "stream",
                ]:
                    kwargs.pop(key, None)
            kwargs.pop("tools", None)
            res = await self.models[model_name](
                messages=messages,
                tools=tool_info,
                response_format=response_format,
                **kwargs,
            )
            if response_format and hasattr(response_format, "model_json_schema"):
                res = response_format.parse_raw(res)
            if tools:
                return await res.__anext__()
            else:
                return res

        # Enqueue the request and wait for result
        return await self._enqueue_request(_invoke_call())
