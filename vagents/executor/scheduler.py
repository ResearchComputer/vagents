"""
scheduler.py

Provides a VScheduler that wraps GraphExecutor to run multiple requests in parallel and yield results as soon as they complete.
"""
import asyncio
from typing import List, AsyncIterator
from vagents.executor import GraphExecutor
from vagents.core import InRequest, OutResponse

class VScheduler:
    """
    Schedule and execute individual InRequest items in parallel using an underlying GraphExecutor. Emits OutResponse as soon as each request finishes.
    """
    def __init__(self):
        # Map module names to their GraphExecutor instances
        self._executors = {}
        # Queue for completed OutResponse objects
        self._response_queue = asyncio.Queue()
        # sets for finished requests
        self._finished_requests = dict()

    async def _run_single(self, req: InRequest) -> OutResponse:
        """
        Offload the synchronous .run([req]) call to a thread pool and return the single result.
        """
        executor = self._executors.get(req.module)
        if executor is None:
            raise RuntimeError(
                f"No executor registered for module '{req.module}'"
            )
        loop = asyncio.get_running_loop()
        result_list = await loop.run_in_executor(
            None, lambda: executor.run([req])
        )
        return result_list[0]

    async def dispatch(self, requests: List[InRequest]) -> AsyncIterator[OutResponse]:
        """
        Accepts a list of InRequest objects and returns an async iterator
        that yields each OutResponse as soon as it's ready.

        Example:
            async for resp in RequestScheduler(compiled, module).dispatch(reqs):
                print(f"Got response {resp.id}: {resp.output}")
        """
        # Create an asyncio.Task for each request
        tasks = [asyncio.create_task(self._run_and_enqueue(r)) for r in requests]
        # as_completed yields each completed future in completion order
        for finished in asyncio.as_completed(tasks):
            # results already enqueued, just drain
            yield await finished
    
    def register_module(self, module_name: str, compiled_graph, module_instance):
        """
        Register a module's compiled graph and instance under the given module name.
        Must be called before dispatching requests for that module.
        """
        self._executors[module_name] = GraphExecutor(compiled_graph, module_instance)

    def add_request(self, req: InRequest):
        """
        Schedule a new request; its result will be enqueued for consumption.
        """
        # Run and enqueue in background
        return asyncio.create_task(self._run_and_enqueue(req))

    async def _run_and_enqueue(self, req: InRequest) -> OutResponse:
        """
        Internal helper: run single request and push result into queue.
        """
        resp = await self._run_single(req)
        await self._response_queue.put(resp)
        return resp

    async def responses(self) -> AsyncIterator[OutResponse]:
        """
        Async iterator that yields each OutResponse as soon as any request completes,
        including those added via add_request.
        """
        while True:
            resp = await self._response_queue.get()
            yield resp
