import os
import asyncio
import logging
import atexit

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "WARN").upper(),
    format="[%(asctime)s]-[%(name)s]-[%(levelname)s]: %(message)s",
)

__GLOBAL_EXECUTOR = None


def get_executor():
    global __GLOBAL_EXECUTOR
    if __GLOBAL_EXECUTOR is None:
        __GLOBAL_EXECUTOR = LMExecutor()
    return __GLOBAL_EXECUTOR


def _shutdown_global_executor():
    """Ensure the global executor is stopped at interpreter exit."""
    global __GLOBAL_EXECUTOR
    try:
        if __GLOBAL_EXECUTOR is not None:
            __GLOBAL_EXECUTOR.stop()
    except Exception:
        # Best-effort cleanup; ignore errors during interpreter shutdown
        pass


# Register shutdown hook
atexit.register(_shutdown_global_executor)


class LMExecutor:
    def __init__(self):
        # all internal queues and states
        self._running = asyncio.PriorityQueue()
        self._waiting = asyncio.PriorityQueue()
        self._task_futures = {}
        self._executor_task: asyncio.Task | None = None
        self._task_counter = 0  # To ensure FIFO order for same priority
        self._loop: asyncio.AbstractEventLoop | None = None
        self._start_executor()

    def _start_executor(self):
        """Start the executor in the background if not already running."""
        if self._executor_task is None or self._executor_task.done():
            try:
                # Get the current event loop
                loop = asyncio.get_running_loop()
                self._loop = loop
                self._executor_task = loop.create_task(self.run())
                logger.debug("Executor task started successfully")
            except RuntimeError:
                # No event loop is running, defer starting until later
                self._executor_task = None
            except Exception as e:
                logger.error(f"Failed to start executor: {e}")
                self._executor_task = None

    def _ensure_loop_bound(self):
        """Reinitialize internal state if the running loop has changed.

        pytest-asyncio often creates a new loop per test function. Asyncio queues
        and tasks are tied to the loop they were created with. To safely support
        multiple loops within a single process (tests), we detect loop changes
        and rebind our queues/background task to the current loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop; nothing to do. We'll lazily start when one exists.
            return

        if self._loop is not None and self._loop is not loop:
            # Different loop detected. Stop previous executor task and reinit queues.
            try:
                if self._executor_task and not self._executor_task.done():
                    self._executor_task.cancel()
            except Exception:
                pass

            # Cancel any pending futures to avoid leaking between loops
            for task, future in list(self._task_futures.items()):
                if not future.done():
                    future.cancel()
            self._task_futures.clear()

            # Recreate loop-bound queues and counters
            self._running = asyncio.PriorityQueue()
            self._waiting = asyncio.PriorityQueue()
            self._task_counter = 0

            # Bind to the new loop and start background runner
            self._loop = loop
            self._executor_task = loop.create_task(self.run())

    def enqueue(self, task: asyncio.Task, priority: int = 10) -> asyncio.Future:
        """Enqueue a task for execution with the specified priority."""
        # Ensure we are running and bound to the current loop
        self._ensure_loop_bound()
        self._start_executor()

        if task.done():
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

        future = asyncio.Future()
        self._task_futures[task] = future

        # Add task to waiting queue with priority and counter for FIFO ordering
        # Format: (priority, counter, task)
        self._task_counter += 1
        try:
            self._waiting.put_nowait((priority, self._task_counter, task))
            logger.debug(f"Task enqueued with priority {priority}")
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            # Clean up the future mapping
            self._task_futures.pop(task, None)
            future.set_exception(RuntimeError(f"Failed to enqueue task: {e}"))

        return future

    def is_healthy(self) -> bool:
        """Check if the executor is running and healthy."""
        return (
            self._executor_task is not None
            and not self._executor_task.done()
            and not self._executor_task.cancelled()
        )

    def get_stats(self) -> dict:
        """Get executor statistics for monitoring."""
        return {
            "is_healthy": self.is_healthy(),
            "waiting_tasks": self._waiting.qsize(),
            "running_tasks": self._running.qsize(),
            "pending_futures": len(self._task_futures),
            "task_counter": self._task_counter,
            "executor_task_done": self._executor_task.done()
            if self._executor_task
            else True,
        }

    async def run(self):
        """Run the executor continuously, processing tasks as they arrive."""
        logger.info("LMExecutor started and running")
        while True:
            try:
                # Wait for a task with a timeout to allow checking for shutdown
                priority_item = await asyncio.wait_for(
                    self._waiting.get(), timeout=10.0
                )
                priority, counter, task = priority_item

                if task.done():
                    # Still need to clean up the future
                    if task in self._task_futures:
                        future = self._task_futures.pop(task)
                        if not future.done():
                            if task.cancelled():
                                future.cancel()
                            elif task.exception() is not None:
                                future.set_exception(task.exception())
                            else:
                                future.set_result(task.result())
                    continue

                self._running.put_nowait((priority, counter, task))
                try:
                    _ = await task
                    logger.debug(f"Task {task} completed successfully.")
                except Exception as task_exception:
                    logger.warning(f"Task failed with exception: {task_exception}")
                    # Don't raise here, handle it in finally block
                finally:
                    # Remove from running queue
                    try:
                        await self._running.get()
                    except Exception as e:
                        logger.error(f"Error removing task from running queue: {e}")

                    # Handle future completion
                    if task in self._task_futures:
                        future = self._task_futures.pop(task)
                        if not future.done():
                            try:
                                if task.cancelled():
                                    future.cancel()
                                else:
                                    exception = task.exception()
                                    if exception is not None:
                                        logger.debug(
                                            f"Setting exception on future: {exception}"
                                        )
                                        future.set_exception(exception)
                                    else:
                                        result = task.result()
                                        logger.debug(
                                            f"Setting result on future: {result}"
                                        )
                                        future.set_result(result)
                            except Exception as future_error:
                                logger.error(
                                    f"Error setting future result/exception: {future_error}"
                                )
                                if not future.done():
                                    future.set_exception(
                                        RuntimeError(
                                            f"Failed to complete task future: {future_error}"
                                        )
                                    )

            except asyncio.TimeoutError:
                # Periodic health check - this is normal
                logger.debug("Executor timeout - continuing...")
                continue
            except asyncio.CancelledError:
                logger.info("Executor task was cancelled")
                break
            except Exception as e:
                # Handle loop shutdown gracefully
                msg = str(e)
                if isinstance(e, RuntimeError) and (
                    "Event loop is closed" in msg or "no running event loop" in msg
                ):
                    logger.info("Event loop closed; stopping LMExecutor loop")
                    break
                logger.error(f"Executor error: {e}", exc_info=True)
                # Don't break the loop unless it's a critical error; but guard sleep
                try:
                    await asyncio.sleep(1)  # Brief pause before retrying
                except RuntimeError:
                    # Loop is closing; exit gracefully
                    break

        logger.info("LMExecutor stopped")

    def stop(self):
        """Stop the executor gracefully."""
        if self._executor_task and not self._executor_task.done():
            logger.info("Stopping LMExecutor...")
            self._executor_task.cancel()
            self._executor_task = None

        # Cancel any remaining futures
        for task, future in list(self._task_futures.items()):
            if not future.done():
                future.cancel()
        self._task_futures.clear()
