import json
import traceback
import asyncio
import aiohttp
import numpy as np
from pydantic import Field
from tqdm.asyncio import tqdm
from dataclasses import dataclass
from typing import Any, Union, Optional, List, Dict
from collections.abc import AsyncGenerator, Iterable

AIOHTTP_TIMEOUT = aiohttp.ClientTimeout(total=6 * 60 * 60)

@dataclass
class CompoundRequest:
    """
    Represents a single inference request for benchmarking.
    """

    id: Union[str, Any]
    module: str
    input: Union[str, Any]
    additional: Optional[Dict[str, Any]] = None


@dataclass
class Metrics:
    completed: int
    overall_throughput: float
    average_latency: float
    success_rate: float


async def get_request(
    input_requests: list[CompoundRequest],
    request_rate: float,
    burstiness: float = 1.0,
) -> AsyncGenerator[CompoundRequest, None]:
    """
    Asynchronously generates requests at a specified rate
    with OPTIONAL burstiness.

    Args:
        input_requests:
            A list of input requests, each represented as a CompoundRequest.
        request_rate:
            The rate at which requests are generated (requests/s).
        burstiness (optional):
            The burstiness factor of the request generation.
            Only takes effect when request_rate is not inf.
            Default value is 1, which follows a Poisson process.
            Otherwise, the request intervals follow a gamma distribution.
            A lower burstiness value (0 < burstiness < 1) results
            in more bursty requests, while a higher burstiness value
            (burstiness > 1) results in a more uniform arrival of requests.
    """
    input_requests: Iterable[CompoundRequest] = iter(input_requests)

    # Calculate scale parameter theta to maintain the desired request_rate.
    assert (
        burstiness > 0
    ), f"A positive burstiness factor is expected, but given {burstiness}."
    theta = 1.0 / (request_rate * burstiness)
    for request in input_requests:
        yield request
        if request_rate == float("inf"):
            # If the request rate is infinity, then we don't need to wait.
            continue
        # Sample the request interval from the gamma distribution.
        # If burstiness is 1, it follows exponential distribution.
        interval = np.random.gamma(shape=burstiness, scale=theta)
        # The next request will be sent after the interval.
        await asyncio.sleep(interval)


@dataclass
class RequestFuncInput:
    api_url: str
    id: str
    module: str
    input: str
    stream: bool
    additional: Optional[Dict[str, Any]] = Field(default_factory=dict)


@dataclass
class RequestFuncOutput:
    output: str = ""
    session: Optional[List] = None

    def dict(self) -> dict[str, Any]:
        return {
            "response": self.output,
            "session": self.session,
        }


async def async_request_backend(
    req_func_input: RequestFuncInput,
    pbar: Optional[tqdm] = None,
) -> RequestFuncOutput:
    api_url = req_func_input.api_url
    async with aiohttp.ClientSession(
        trust_env=True, timeout=AIOHTTP_TIMEOUT
    ) as session:
        payload = {
            "module": req_func_input.module,
            "input": req_func_input.input,
            "additional": req_func_input.additional,
        }
        output = RequestFuncOutput()
        try:
            start = asyncio.get_event_loop().time()
            async with session.post(f"{api_url}/v1/responses", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    end = asyncio.get_event_loop().time()
                    print(data)
                    output.output = data[0]['output']
                    output.session = data[0]['session']
                    
                else:
                    output.error = f"Error: {resp.status}"
        except Exception as e:
            print(f"Response data: {data}, request: {payload}")
            traceback.print_exc()
            output.error = str(e)
        if pbar:
            pbar.update(1)
        return output

def read_jsonl(file_path, skip_invalid=True):
    """Read JSONL file and return list of JSON objects."""
    data = []
    with open(file_path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                if skip_invalid:
                    continue
                else:
                    raise ValueError(f"Invalid JSON: {line}")
    return data