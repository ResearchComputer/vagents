import asyncio
import time
from datetime import datetime
from vagents.managers.model_manager import LMManager
from vagents.core import LLM, Message
import os


async def simple_test():
    """Simple test to verify concurrency behavior."""
    # Initialize manager with 20 concurrent requests
    manager = LMManager(max_concurrent_requests=20)

    manager.add_model(
        LLM(
            model_name="Qwen/Qwen3-32B",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        )
    )

    print(
        f"Manager initialized with max_concurrent_requests: {manager.max_concurrent_requests}"
    )
    print(f"Initial queue status: {manager.get_queue_status()}")

    # Create 25 simple requests to test the 20 limit
    requests = [f"Count to {i}" for i in range(1, 26)]

    async def make_request(request_id, prompt):
        start_time = time.time()
        print(
            f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Starting request {request_id}: {prompt}"
        )

        try:
            response = await manager.call(
                "Qwen/Qwen3-32B", [Message(role="user", content=prompt)]
            )
            end_time = time.time()
            print(
                f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Completed request {request_id} in {end_time - start_time:.2f}s"
            )
            return request_id, response
        except Exception as e:
            end_time = time.time()
            print(
                f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Failed request {request_id} in {end_time - start_time:.2f}s: {e}"
            )
            return request_id, f"Error: {e}"

    # Create all tasks
    tasks = [
        asyncio.create_task(make_request(i + 1, prompt))
        for i, prompt in enumerate(requests)
    ]

    # Monitor queue status for a few seconds
    async def monitor():
        for _ in range(10):  # Monitor for 10 seconds
            status = manager.get_queue_status()
            print(
                f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Queue: {status['queue_size']}, Active: {status['active_requests']}, Max: {status['max_concurrent_requests']}"
            )
            await asyncio.sleep(1)

    monitor_task = asyncio.create_task(monitor())

    # Wait for all requests
    results = await asyncio.gather(*tasks, return_exceptions=True)
    monitor_task.cancel()

    print(f"\nCompleted {len(results)} requests")
    await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(simple_test())
