import argparse
from typing import List

async def benchmark(args: argparse.Namespace)->None:
    print(args)

if __name__=="__main__":

    import asyncio
    parser = argparse.ArgumentParser(description="Benchmark behavior of a vagent server.")
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:8001/v1"
    )
    parser.add_argument(
        "--configs",
        type=List[str],
        default=[
            "benchmarks.configs.deep_research.json",
            "vagents.contrib.agent_search"
        ],
        nargs="+",
    )
    
    args = parser.parse_args()
    