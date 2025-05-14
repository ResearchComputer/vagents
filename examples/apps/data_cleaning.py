import os
from typing import List
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, LLM
from vagents.executor import GraphExecutor, compile_to_graph
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
        res = await res.__anext__()
        return OutResponse(
            output=f"{query.input}\n\n{res}",
            id=query.id,
            input=query.input,  
            module=query.module,
        )

if __name__ == "__main__":
    import asyncio
    sft_dc_module = SFTDataCleaning()
    query = InRequest(
        id="1",
        input={"prompt": "What is the capital of France?"},
        module="SFTDataCleaning"
    )
    compiled_dr = compile_to_graph(sft_dc_module.forward)
    start = timer()
    response = asyncio.run(sft_dc_module.forward(query))
    print(f"Response: {response.output}")
    end = timer()
    print(f"Time taken: {end - start} seconds")
    ge = GraphExecutor(compiled_dr, module_instance=sft_dc_module)
    outputs = ge.run([
        InRequest(
            id="test_query",
            input={"prompt": "What is the capital of France?"},
            module="SFTDataCleaning",
        )
    ])
    end = timer()
    print(f"GraphExecutor Response: {outputs[0].output}, elapsed time: {end - start} seconds")