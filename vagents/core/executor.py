import asyncio

__GLOBAL_EXECUTOR = None

def get_executor():
    global __GLOBAL_EXECUTOR
    if __GLOBAL_EXECUTOR is None:
        __GLOBAL_EXECUTOR = LMExecutor()
    return __GLOBAL_EXECUTOR

class LMExecutor:
    def __init__(self):
        self._running = asyncio.PriorityQueue()
        self._waiting = asyncio.PriorityQueue()
        self._task_futures = {}
        self._executor_task: asyncio.Task | None = None
        self._task_counter = 0  # To ensure FIFO order for same priority
        self._start_executor()
    
    def _start_executor(self):
        """Start the executor in the background if not already running."""
        if self._executor_task is None or self._executor_task.done():
            try:
                # Get the current event loop
                loop = asyncio.get_running_loop()
                self._executor_task = loop.create_task(self.run())
            except RuntimeError:
                # No event loop is running, defer starting until later
                self._executor_task = None
        
    def enqueue(self, task: asyncio.Task, priority: int = 10) -> asyncio.Future:
        # Ensure executor is running
        self._start_executor()
        
        if task.done():
            # Create a future and set its result immediately
            future = asyncio.Future()
            if task.cancelled():
                future.cancel()
            else:
                exception = task.exception()
                if exception is not None:
                    future.set_exception(exception)
                else:
                    future.set_result(task.result())
            return future
        
        # Create a future for this task
        future = asyncio.Future()
        self._task_futures[task] = future
        
        # Add task to waiting queue with priority and counter for FIFO ordering
        # Format: (priority, counter, task)
        self._task_counter += 1
        self._waiting.put_nowait((priority, self._task_counter, task))
        
        return future
    
    async def run(self):
        """Run the executor continuously, processing tasks as they arrive."""
        while True:
            try:
                # Wait for a task with a timeout to allow checking for shutdown
                priority_item = await asyncio.wait_for(self._waiting.get(), timeout=1.0)
                priority, counter, task = priority_item
                
                if task.done():
                    continue
                    
                self._running.put_nowait((priority, counter, task))
                try:
                    await task
                except Exception as e:
                    print(f"Task failed with exception: {e}")
                finally:
                    await self._running.get()  # Remove from running queue
                    # Signal that the task is complete via the future
                    if task in self._task_futures:
                        future = self._task_futures.pop(task)
                        if not future.done():
                            if task.cancelled():
                                future.cancel()
                            else:
                                exception = task.exception()
                                if exception is not None:
                                    future.set_exception(exception)
                                else:
                                    future.set_result(task.result())
                                    
            except asyncio.TimeoutError:
                # No tasks available, continue waiting
                continue
            except Exception as e:
                print(f"Executor error: {e}")
                # Continue running even if there's an error
    
    def stop(self):
        if self._executor_task and not self._executor_task.done():
            self._executor_task.cancel()
            self._executor_task = None