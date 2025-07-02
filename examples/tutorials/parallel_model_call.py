import asyncio
import json
import time
from datetime import datetime
from vagents.managers.model_manager import LMManager
from vagents.core import LLM, Message
import os

# Initialize manager with concurrency control
manager = LMManager(max_concurrent_requests=33)  # Set directly in constructor

manager.add_model(
    LLM(
        model_name="Qwen/Qwen3-32B",
        base_url=os.environ.get("RC_API_BASE", ""),
        api_key=os.environ.get("RC_API_KEY", ""),
    )
)

# Create different requests
REQUESTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms.",
    "Write a haiku about programming.",
    "What are the benefits of renewable energy?",
    "How does machine learning work?",
    "What is the history of the internet?",
    "Explain the theory of relativity.",
    "What are the main components of a computer?",
    "How do neural networks function?",
    "What is climate change?",
    "Explain blockchain technology.",
    "What are the principles of good software design?",
    "How does photosynthesis work?",
    "What is artificial intelligence?",
    "Explain the water cycle.",
    "What are the different types of databases?",
    "How do vaccines work?",
    "What is the scientific method?",
    "Explain supply and demand economics.",
    "What are the layers of the Earth's atmosphere?",
    "What is the significance of the Turing test?",
    "What is the difference between supervised and unsupervised learning?",
    "How do cryptocurrencies work?",
    "What is the role of a compiler in programming?",
    "What is the difference between HTTP and HTTPS?",
    "What is the purpose of version control systems?",
    "How do search engines work?",
    "What is the difference between a stack and a queue?",
    "What is the role of an operating system?",
    "What is the difference between front-end and back-end development?",
    "What is the purpose of a database index?",
    "What is the difference between a class and an object in OOP?",
    "What is the role of APIs in software development?",
]
print(f"{len(REQUESTS)} requests created for parallel processing.")

# Global counter for completed requests
completed_count = 0
completed_lock = asyncio.Lock()


async def process_single_request(request_id: int, prompt: str):
    """Process a single request and return the result with metadata."""
    global completed_count
    start_time = time.time()

    try:
        print(f"Starting request {request_id + 1}: {prompt[:50]}...")

        # Log when we start the actual model call
        call_start = time.time()
        response = await manager.call(
            "Qwen/Qwen3-32B", [Message(role="user", content=prompt)]
        )
        call_end = time.time()

        end_time = time.time()
        processing_time = end_time - start_time
        actual_call_time = call_end - call_start

        result = {
            "request_id": request_id + 1,
            "prompt": prompt,
            "response": response,
            "processing_time_seconds": round(processing_time, 2),
            "actual_call_time_seconds": round(actual_call_time, 2),
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }

        # Increment completed counter
        async with completed_lock:
            completed_count += 1

        print(
            f"Completed request {request_id + 1} in {processing_time:.2f}s (call: {actual_call_time:.2f}s)"
        )
        return result

    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time

        result = {
            "request_id": request_id + 1,
            "prompt": prompt,
            "response": None,
            "error": str(e),
            "processing_time_seconds": round(processing_time, 2),
            "timestamp": datetime.now().isoformat(),
            "status": "error",
        }

        # Increment completed counter even for failed requests
        async with completed_lock:
            completed_count += 1

        print(f"Failed request {request_id + 1}: {str(e)}")
        return result


async def monitor_progress(total_requests: int):
    """Monitor and display progress of request processing."""
    global completed_count
    while True:
        status = manager.get_queue_status()

        async with completed_lock:
            current_completed = completed_count

        print(
            f"\rProgress: {current_completed}/{total_requests} completed | "
            f"Queue: {status['queue_size']} | "
            f"Active: {status['active_requests']}",
            end="",
        )

        if current_completed >= total_requests:
            print()  # New line after completion
            break

        await asyncio.sleep(1)


async def main():
    global completed_count
    # Reset completed counter
    completed_count = 0

    print(f"Starting parallel processing of {len(REQUESTS)} requests...")
    print(f"Max concurrent requests: {manager.max_concurrent_requests}")
    print(f"Queue status at start: {manager.get_queue_status()}")
    print("-" * 60)

    start_time = time.time()

    # Create tasks for all requests
    tasks = [
        asyncio.create_task(process_single_request(i, prompt))
        for i, prompt in enumerate(REQUESTS)
    ]

    # Wait a moment to see initial batch behavior
    await asyncio.sleep(0.1)
    print(f"Queue status after 0.1s: {manager.get_queue_status()}")

    # Start progress monitoring
    monitor_task = asyncio.create_task(monitor_progress(len(REQUESTS)))

    # Wait for all requests to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Stop monitoring
    monitor_task.cancel()

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\nAll requests completed in {total_time:.2f} seconds")

    # Process results and separate successful from failed
    successful_results = []
    failed_results = []

    for result in results:
        if isinstance(result, Exception):
            failed_results.append(
                {
                    "error": str(result),
                    "timestamp": datetime.now().isoformat(),
                    "status": "exception",
                }
            )
        elif result["status"] == "success":
            successful_results.append(result)
        else:
            failed_results.append(result)

    # Create summary
    summary = {
        "execution_summary": {
            "total_requests": len(REQUESTS),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "total_execution_time_seconds": round(total_time, 2),
            "average_processing_time_seconds": round(
                sum(r["processing_time_seconds"] for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                2,
            ),
            "average_actual_call_time_seconds": round(
                sum(r.get("actual_call_time_seconds", 0) for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                2,
            ),
            "requests_per_second": round(len(REQUESTS) / total_time, 2),
            "timestamp": datetime.now().isoformat(),
        },
        "successful_results": successful_results,
        "failed_results": failed_results,
    }

    # Write results to file
    output_filename = (
        f"parallel_model_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nResults written to: {output_filename}")
    print(f"Summary:")
    print(f"  - Total requests: {summary['execution_summary']['total_requests']}")
    print(f"  - Successful: {summary['execution_summary']['successful_requests']}")
    print(f"  - Failed: {summary['execution_summary']['failed_requests']}")
    print(
        f"  - Total time: {summary['execution_summary']['total_execution_time_seconds']}s"
    )
    print(
        f"  - Average processing time: {summary['execution_summary']['average_processing_time_seconds']}s"
    )
    print(
        f"  - Average actual call time: {summary['execution_summary']['average_actual_call_time_seconds']}s"
    )
    print(
        f"  - Requests per second: {summary['execution_summary']['requests_per_second']}"
    )
    # Gracefully shutdown the manager
    await manager.shutdown()
    return summary


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        print("\nExecution completed successfully!")
    except KeyboardInterrupt:
        print("\nExecution interrupted by user")
    except Exception as e:
        print(f"\nExecution failed with error: {e}")
