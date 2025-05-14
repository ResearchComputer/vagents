import os
from typing import List
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, LLM
from vagents.executor import GraphExecutor, compile_to_graph, VScheduler
from vagents.managers import LMManager
from timeit import default_timer as timer

def is_self_awareness(query: str) -> str:
    """
    You are a helpful assistant in verifying if this query is self-awareness related.
    Return `yes` if the query is self-awareness related, otherwise return `no`.
    Do not include any other information.
    """
    return f"query: {query}\n\nself-awareness: "
    

class SFTDataCleaning(VModule):
    def __init__(self):
        super().__init__(config=VModuleConfig(enable_async=False))
        llm = LLM(
            model_name="Qwen/Qwen3-32B",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        )
        self.models = LMManager()
        self.models.add_model(llm)
    
    async def forward(self, query: InRequest) -> OutResponse:
        res = await self.models.invoke(
            is_self_awareness,
            model_name="Qwen/Qwen3-32B",
            query=query.input['prompt'],
        )
        return OutResponse(
            output=f"{query.input['prompt']}\n\n{res}",
            id=query.id,
            input=query.input,  
            module=query.module,
        )

if __name__ == "__main__":
    import asyncio

    num_queries = 10
    sft_dc_module = SFTDataCleaning()
    compiled_dr = compile_to_graph(sft_dc_module.forward)

    # 1) build & register scheduler
    scheduler = VScheduler()
    scheduler.register_module(
        module_name="SFTDataCleaning",
        compiled_graph=compiled_dr,
        module_instance=sft_dc_module,
    )

    async def main():
        # 2) prepare your list of requests
        requests = [
            InRequest(
                id=f"q{i}",
                input={"prompt": "What is the capital of France?"},
                module="SFTDataCleaning",
            )
            for i in range(num_queries)
        ]

        # --- Option A: fixed‐batch, fire & consume via dispatch() ---
        start = timer()
        async for resp in scheduler.dispatch(requests):
            print(f"[dispatch] got {resp.id}: {resp.output}")
        elapsed = timer() - start
        print(f"Total dispatch time: {elapsed:.2f}s")

        # --- Option B: dynamic pool, add then consume via responses() ---
        # clear any previous state
        # (re-enqueue if you want to interleave new requests at runtime)
        for req in requests:
            scheduler.add_request(req)

        start = timer()
        count = 0
        async for resp in scheduler.responses():
            print(f"[responses] got {resp.id}: {resp.output}")
            count += 1
            if count >= num_queries:
                break
        elapsed = timer() - start
        print(f"Total dynamic time: {elapsed:.2f}s")

    asyncio.run(main())