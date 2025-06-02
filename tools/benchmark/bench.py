import json
import argparse
from typing import List
from tqdm.asyncio import tqdm

from vagents.utils import VClient
from tools.benchmark.utils import CompoundRequest, Metrics, get_request, async_request_backend, RequestFuncInput, RequestFuncOutput

async def benchmark(args: argparse.Namespace)->None:
    print(args)
    # register all modules
    cfgs = []
    client = VClient(
        base_url = args.endpoint,
        api_key=args.api_key
    )
    for config in args.configs:
        with open(config, "r") as f:
            cfg = json.load(f)
            cfgs.append(cfg)
            client.register_module(
                path=cfg['module'],
                force=False,
                mcp_configs=cfg.get('mcp_configs', []),
            )
    
    requests = [
        CompoundRequest(
            id=f"request_{i}",
            module='vagents.contrib.modules.deep_research:DeepResearch',
            input='Roast Xiaozhe Yao\'s Research, in a very cynical and sarcastic tone.',
            additional=cfg.get('additional', {}),
        ) for i in range(10)
    ]
    pbar = tqdm(total=len(requests))
    tasks: list[asyncio.Task] = []
    semaphore = (
        asyncio.Semaphore(args.max_concurrency) if args.max_concurrency else None
    )

    async def limited_request_func(req_func_input, pbar):
        if semaphore is None:
            return await async_request_backend(req_func_input=req_func_input, pbar=pbar)
        async with semaphore:
            return await async_request_backend(req_func_input=req_func_input, pbar=pbar)

    async for request in get_request(
        requests, request_rate=args.request_rate, burstiness=args.burstiness
    ):
        req_func_input = RequestFuncInput(
            api_url=args.endpoint,
            input=request.input,
            module=request.module,
            id=request.id,
            additional=request.additional,
            stream=False,
        )
        tasks.append(
            asyncio.create_task(
                limited_request_func(req_func_input=req_func_input, pbar=pbar)
            )
        )
    outputs: List[RequestFuncOutput] = await asyncio.gather(*tasks)
    print(outputs)
if __name__=="__main__":
    import asyncio
    parser = argparse.ArgumentParser(description="Benchmark behavior of a vagent server.")
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:8001"
    )
    parser.add_argument(
        "--configs",
        type=List[str],
        default=[
            "meta/benchmarks/configs/deep_research.json",
        ],
        nargs="+",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
    )
    parser.add_argument(
        "--request-rate", type=float, default=1.0, help="Request rate in requests/s"
    )
    parser.add_argument(
        "--burstiness", type=float, default=1.0, help="Burstiness factor"
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        required=False,
        default=None,
        help="Max concurrency for the agent",
    )
    args = parser.parse_args()
    asyncio.run(benchmark(args))