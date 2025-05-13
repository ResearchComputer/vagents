import os
import subprocess
import zmq
import asyncio
import zmq.asyncio
import uuid
from typing import List, Union, Dict, Any, Optional, Tuple

from .worker_manager import DockerWorkerManager
from .utils import get_zmq_socket, get_ipc_endpoint
from vagents.utils import logger, Profiler

JOB_DISPATCH_TIMEOUT = int(os.environ.get("VAGENT_JOB_DISPATCH_TIMEOUT", 120))
WORKER_STARTUP_TIMEOUT = int(os.environ.get("VAGENT_WORKER_STARTUP_TIMEOUT", 30))


class CodeExecutorManager(DockerWorkerManager):
    def __init__(self):
        super().__init__()
        self.context = zmq.asyncio.Context(2)
        self.task_socket_endpoint = "ipc:///tmp/vagent_task"
        self.task_socket = get_zmq_socket(
            self.context, zmq.PUB, self.task_socket_endpoint
        )
        self.result_sockets = {}
        self.result_queues = {}  # Queues for per-session results
        self.listener_tasks = {}  # background listener tasks per session
        self.running_workers = set()
        self.records = {}

    async def maybe_start_worker(self, session_id: str) -> bool:
        """Start a worker if it's not already running.
        Args:
            session_id: The ID of the worker session.
        Returns:
            bool: True if the worker was successfully started or was already running.
        Raises:
            TimeoutError: If the worker fails to start within the timeout.
        """
        if session_id in self.running_workers:
            return True
        with Profiler(session_id=session_id, name="start-worker") as p:
            try:
                # Start the worker container
                self.running_workers.add(session_id)
                await self.start_worker(
                    worker_id=session_id,
                    worker_owner="vagent",
                    worker_image="ghcr.io/xiaozheyao/vagent.base:0.0.1",
                    worker_command=[
                        "python",
                        "-m",
                        "vagents.services.code_svc.worker",
                        session_id,
                        "--zmq-endpoint",
                        f"{self.task_socket_endpoint}",
                        "--result-endpoint",
                        get_ipc_endpoint(session_id),
                    ],
                    bind_tmp=True,
                )
                # Wait for the initial message from the worker without timeout
                try:
                    result = await self._listen_results(session_id, timeout=None)
                    if "status" in result and result.get("status") == "ok":
                        logger.debug(
                            f"Worker {session_id} started successfully and is ready."
                        )
                        # Initialize result queue and start background listener
                        self.result_queues[session_id] = asyncio.Queue()
                        # start and track listener task
                        task = asyncio.create_task(self._result_listener(session_id))
                        self.listener_tasks[session_id] = task
                        return True
                    else:
                        logger.warning(
                            f"Worker {session_id} sent unexpected initial message: {result}"
                        )
                        return session_id in self.running_workers
                except asyncio.TimeoutError:
                    logger.error(f"Timed out waiting for worker {session_id} to start")
                    await self.cleanup(session_id)
                    raise TimeoutError(
                        f"Worker {session_id} failed to start within {WORKER_STARTUP_TIMEOUT} seconds"
                    )
            except Exception as e:
                logger.error(f"Error starting worker {session_id}: {e}")
                raise

    async def dispatch(self, session_id: str, job: Dict[str, Any]):
        import asyncio

        """Dispatch a job to a worker and wait for the result with a unique job ID."""
        try:
            # Ensure the worker is started and ready
            await self.maybe_start_worker(session_id)
            # Assign unique job ID
            job_id = str(uuid.uuid4())
            logger.debug(f"Dispatching job {job_id} to worker {session_id}")
            with Profiler(session_id=session_id, name="execute-job") as p:
                # Send the job with its ID to the worker
                await self.task_socket.send_json(
                    {"session_id": session_id, "job_id": job_id, "job": job}
                )
                # Wait for the matching result from the queue
                try:
                    while True:
                        res = await asyncio.wait_for(
                            self.result_queues[session_id].get(),
                            timeout=JOB_DISPATCH_TIMEOUT,
                        )
                        if res.get("job_id") == job_id:
                            break
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Timeout waiting for response of job {job_id} on session {session_id}"
                    )
                    return 1, "timeout"

            # Record the job and response
            if session_id not in self.records:
                self.records[session_id] = []
            self.records[session_id].append(
                {
                    "job": job,
                    "response": res,
                }
            )
            return res["code"], res["output"]
        except Exception as e:
            logger.error(f"Error dispatching job to worker {session_id}: {e}")
            return 1, f"Error: {str(e)}"

    async def _listen_results(self, session_id: str, timeout: Optional[int] = None):
        """Listen for results from a worker.  Deprecated once queue listener is in place."""
        # Create socket if it doesn't exist
        if session_id not in self.result_sockets:
            result_socket = get_zmq_socket(
                self.context, zmq.PULL, get_ipc_endpoint(session_id)
            )
            # drop pending messages on close
            result_socket.setsockopt(zmq.LINGER, 0)
            self.result_sockets[session_id] = result_socket
            # Note: result queue listener will handle incoming messages
        else:
            result_socket = self.result_sockets[session_id]

        # Receive a single message (e.g., initial status) with optional timeout
        if timeout is not None:
            msg = await asyncio.wait_for(result_socket.recv_json(), timeout=timeout)
        else:
            msg = await result_socket.recv_json()
        return msg

    async def _result_listener(self, session_id: str):
        """Background task: read all messages and enqueue into the session's result queue."""
        socket = self.result_sockets.get(session_id)
        queue = self.result_queues.get(session_id)
        try:
            while session_id in self.running_workers and socket and queue:
                msg = await socket.recv_json()
                if msg.get("job_id"):
                    await queue.put(msg)
        except asyncio.CancelledError:
            logger.debug(f"Result listener for {session_id} cancelled")
        except Exception as e:
            logger.error(f"Error in result listener for {session_id}: {e}")
        # exit when cancelled or on error

    async def cleanup(self, session_ids: Union[str, List[str]]):
        """Clean up workers by stopping their containers and cleaning up sockets."""
        previous_running_workers = len(self.running_workers)
        previous_running_containers = int(
            subprocess.check_output("docker ps -a | wc -l", shell=True).strip()
        )
        if isinstance(session_ids, str):
            session_ids = [session_ids]

        for session_id in session_ids:
            if session_id not in self.running_workers:
                logger.info(f"Worker {session_id} is not running, skipping cleanup.")
                continue
            try:
                await self.stop_worker(session_id)
                # also cancel queue and listener
                self.result_queues.pop(session_id, None)
                # cancel listener task
                task = self.listener_tasks.pop(session_id, None)
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                if session_id in self.running_workers:
                    self.running_workers.remove(session_id)
                # Clean up the socket and lock
                socket = self.result_sockets.pop(session_id, None)
                if socket:
                    # close without waiting for pending messages
                    socket.close(linger=0)
                current_running_containers = int(
                    subprocess.check_output("docker ps -a | wc -l", shell=True).strip()
                )
                logger.info(
                    f"Worker {session_id} stopped and cleaned up. Running workers: {previous_running_workers} -> {len(self.running_workers)}. Running containers: {previous_running_containers} -> {current_running_containers}"
                )
            except Exception as e:
                logger.info(f"Error cleaning up worker {session_id}: {e}")

    def cleanup_sync(self, session_ids: Union[str, List[str]]):
        """Synchronous version of cleanup for use in non-async contexts."""
        if isinstance(session_ids, str):
            session_ids = [session_ids]
        for session_id in session_ids:
            try:
                # Create a new event loop for running the stop_worker coroutine
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.stop_worker(session_id))
                loop.close()

                if session_id in self.running_workers:
                    self.running_workers.remove(session_id)

                # Clean up the socket and lock
                socket = self.result_sockets.pop(session_id, None)
                if socket:
                    socket.close()
                logger.debug(f"Worker {session_id} stopped and cleaned up.")
            except Exception as e:
                logger.error(f"Error cleaning up worker {session_id}: {e}")
