import asyncio
import time
import zmq
import zmq.asyncio
import argparse  # new import
from vagents.utils import logger
from vagents.managers.utils import get_zmq_socket, run_command


class VWorker:
    def __init__(self, name, zmq_endpoint, result_endpoint):
        self.zmq_endpoint = zmq_endpoint
        self.name = name
        self.result_endpoint = result_endpoint
        context = zmq.asyncio.Context.instance(2)
        self.socket = get_zmq_socket(context, zmq.SUB, self.zmq_endpoint)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.result_socket = get_zmq_socket(context, zmq.PUSH, self.result_endpoint)
        self.result_socket.setsockopt(zmq.LINGER, 0)

    async def listen_tasks(self):
        # Allow subscription to propagate, then notify ready
        await asyncio.sleep(0.1)
        await self.on_ready()
        while True:
            try:
                task = await self.socket.recv_json()
                if "session_id" in task:
                    if task["session_id"] == self.name:
                        logger.warning(f"executing task: {task}")
                        # Execute task and propagate job_id
                        code, output = await self.execute_task(task["job"])
                        logger.warning(f"Task result: {code} {output}")
                        # Send result including job_id
                        await self.result_socket.send_json(
                            {
                                "session_id": self.name,
                                "job_id": task.get("job_id"),
                                "code": code,
                                "output": output,
                            }
                        )
                        logger.warning(f"reply: {code} {output}")
                    else:
                        pass
                elif "status" in task:
                    logger.warning(f"Received status message: {task}")
                else:
                    logger.warning("Error receiving task with no session_id")
            except Exception:
                logger.error("Error receiving task")
            await asyncio.sleep(0.1)

    async def execute_task(self, task):
        # Execute the task here
        if task["action"] == "bash":
            command = task["content"]
            logger.debug(f"Executing command: {command}")
            code, output = run_command(command)
            return code, output
        elif task["action"] == "mcp":
            logger.debug(f"Executing mcp command: {task['content']}")
        else:
            logger.error(f"Unknown task action: {task['action']}")
            return -1, "Unknown task action"

    async def on_ready(self):
        # Send initial ready status
        await self.result_socket.send_json({"id": self.name, "status": "ok"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="Worker name")
    parser.add_argument(
        "--zmq-endpoint",
        default="tcp://host.docker.internal:5556",
        help="ZMQ endpoint for receiving tasks",
    )
    parser.add_argument(
        "--result-endpoint",
        default="ipc://worker_result",
        help="ZMQ endpoint for sending task results",
    )
    args = parser.parse_args()
    logger.warning(f"args: {args}")
    worker = VWorker(
        name=args.name,
        zmq_endpoint=args.zmq_endpoint,
        result_endpoint=args.result_endpoint,
    )

    async def start_worker():
        await worker.listen_tasks()

    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped manually.")
