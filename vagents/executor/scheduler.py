"""
scheduler.py

Provides a VScheduler that wraps GraphExecutor to run multiple requests in parallel and yield results as soon as they complete.
"""
import asyncio
from typing import List, AsyncIterator, Dict, Any

from vagents.utils import logger
from vagents.executor import GraphExecutor
from vagents.core import InRequest, OutResponse

class VScheduler:
    """
    Schedule and execute individual InRequest items in parallel using an underlying GraphExecutor. Emits OutResponse as soon as each request finishes.
    """
    def __init__(self):
        # Map module names to their GraphExecutor instances
        self._executors: Dict[str, GraphExecutor] = {} # Type hint for clarity
        # Queue for completed OutResponse objects
        self._response_queue: asyncio.Queue[OutResponse] = asyncio.Queue() # Type hint for clarity
        # sets for finished requests
        self._finished_requests: Dict[str, asyncio.Task[OutResponse]] = dict() # Type hint for clarity

    async def _run_single(self, req: InRequest) -> OutResponse:
        """
        Run a single request using the appropriate GraphExecutor.
        If req.stream is True, the OutResponse.output will be an AsyncGenerator.
        If req.stream is False, the OutResponse.output will be an aggregated string.
        """
        executor = self._executors.get(req.module)
        if executor is None:
            logger.error(f"No executor registered for module '{req.module}' for request ID '{req.id}'")
            # Return an error OutResponse
            return OutResponse(
                id=req.id,
                input=req.input,
                module=req.module,
                output=f"Error: No executor registered for module '{req.module}'.",
                error=f"No executor registered for module '{req.module}'.",
                session_history=[] # Ensure all required fields are present
            )

        response_item_generator = executor.run([req]) # This is an AsyncGenerator[Union[str, OutResponse], Any]

        if req.stream:
            # For streaming, the handler expects final_out_response.output to be the stream.
            # We pass the generator directly. Metadata comes from req.
            # If executor.run yields a final OutResponse, its metadata isn't easily merged here
            # without consuming the generator, which we don't want to do for streaming here.
            # The GraphExecutor.run should ideally yield a final OutResponse whose .output IS the stream if that's the pattern.
            # For now, we assume the handler will deal with a raw stream if it gets one.
            # The OutResponse model allows output to be an AsyncGenerator.
            logger.debug(f"Scheduler: Streaming request {req.id} for module {req.module}. Output will be an async generator.")
            return OutResponse(
                id=req.id,
                input=req.input,
                module=req.module,
                output=response_item_generator, # Pass the generator as output
                session_history=[] # Use empty list as default
            )
        else:
            # Non-streaming: aggregate all parts.
            all_data_chunks: List[str] = []
            # Initialize with data from the original request
            final_response_data = {
                "id": req.id,
                "input": req.input,
                "module": req.module,
                "session_history": [], # Use empty list as default
                "error": None,
                "output": None # Will be replaced by aggregated string
            }

            try:
                async for item in response_item_generator:
                    if isinstance(item, str):
                        all_data_chunks.append(item)
                    elif isinstance(item, OutResponse):
                        # Merge metadata from the OutResponse yielded by the executor
                        # Prioritize executor's version for fields it might update (e.g., session_history, error)
                        final_response_data["id"] = item.id or final_response_data["id"]
                        if hasattr(item, 'input') and item.input is not None : final_response_data["input"] = item.input
                        final_response_data["module"] = item.module or final_response_data["module"]
                        final_response_data["session_history"] = item.session_history or final_response_data["session_history"]
                        final_response_data["error"] = item.error or final_response_data["error"]
                        # Do not take item.output here, we are aggregating string chunks
                        if item.output and isinstance(item.output, str) and not all_data_chunks: # If executor gives a full string output
                            all_data_chunks.append(item.output)


            except Exception as e:
                logger.error(f"Scheduler: Error consuming response generator for req {req.id}, module {req.module}: {e}", exc_info=True)
                final_response_data["error"] = str(e)
                final_response_data["output"] = "".join(all_data_chunks) + f"\\nError during execution: {e}"
                return OutResponse(**final_response_data)

            final_output_str = "".join(all_data_chunks)
            final_response_data["output"] = final_output_str
            logger.debug(f"Scheduler: Non-streaming request {req.id} for module {req.module}. Aggregated output length: {len(final_output_str)}.")
            return OutResponse(**final_response_data)

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
        for finished_task in asyncio.as_completed(tasks):
            # results already enqueued by _run_and_enqueue,
            # this await is for the task completion itself (which returns OutResponse)
            try:
                yield await finished_task
            except Exception as e:
                # If _run_and_enqueue or _run_single raised an unhandled exception
                logger.error(f"Scheduler: Exception in dispatched task: {e}", exc_info=True)
                # Attempt to find which request failed if possible, though task doesn't directly hold req
                # This error should ideally be caught within _run_single and returned as an OutResponse with an error field.
                # If it reaches here, it's an unexpected scheduler error.
                # We could yield a generic error OutResponse if we had the req.id
                pass


    def register_module(self, module_name: str, compiled_graph: Any, module_instance: Any) -> None: # Graph type can be 'Graph'
        """
        Register a module's compiled graph and instance under the given module name.
        Must be called before dispatching requests for that module.
        """
        if not compiled_graph and not module_instance.forward: # Ensure there's something to execute
             logger.warning(f"Scheduler: Module {module_name} has no compiled_graph and no forward method on instance. Cannot register.")
             return
        self._executors[module_name] = GraphExecutor(compiled_graph, module_instance)
        logger.info(f"Scheduler: Module {module_name} registered with executor.")


    def add_request(self, req: InRequest) -> asyncio.Task[OutResponse]:
        """
        Schedule a new request; its result will be enqueued for consumption by `responses()`
        or can be awaited directly from the returned task.
        """
        # Run and enqueue in background, also return the task
        task: Task[OutResponse] = asyncio.create_task(self._run_and_enqueue(req))
        self._finished_requests[req.id] = task
        return task

    async def _run_and_enqueue(self, req: InRequest) -> OutResponse:
        """
        Internal helper: run single request and push result into queue.
        Also returns the response for direct awaiting if needed (e.g. by add_request or dispatch).
        """
        try:
            resp = await self._run_single(req)
        except Exception as e:
            logger.error(f"Scheduler: Unhandled error in _run_single for req {req.id}, module {req.module}: {e}", exc_info=True)
            resp: OutResponse = OutResponse(
                id=req.id,
                input=req.input,
                module=req.module,
                output=f"Critical error in scheduler processing request: {e}",
                error=f"Critical scheduler error: {str(e)}",
                session_history=[] # Use empty list as default
            )
        
        await self._response_queue.put(resp)
        # Remove from finished_requests once enqueued, or let it be cleaned up elsewhere if needed.
        # self._finished_requests.pop(req.id, None) # Clean up if task is considered done after enqueuing
        return resp

    async def responses(self) -> AsyncIterator[OutResponse]:
        """
        Async iterator that yields each OutResponse as soon as any request completes,
        including those added via add_request.
        """
        while True:
            resp: OutResponse = await self._response_queue.get()
            yield resp
            self._response_queue.task_done() 
            # Notify queue that item processing is complete
            # Clean up from finished_requests if the task is truly done.
            # This might need more robust tracking if tasks can be cancelled or have other states.
            # For now, popping here assumes one response per request.
            if resp.id in self._finished_requests:
                 del self._finished_requests[resp.id]
