import os
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, LLM
from vagents.executor import compile_to_graph, VScheduler, Graph
from vagents.managers import LMManager

class ChatModule(VModule):
    def __init__(self) -> None:
        super().__init__(config=VModuleConfig(enable_async=False))
        llm: LLM = LLM(
            model_name="Qwen/Qwen3-32B",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        )
        self.models = LMManager()
        self.models.add_model(llm)        

    async def forward(self, query: InRequest) -> OutResponse:
        res = await self.models.call(
            "Qwen/Qwen3-32B",
            messages=[{"role": "user", "content": query.input}],
            stream=query.stream
        )
        return OutResponse(
            output=res,
            id=query.id,
            input=query.input,  
            module=query.module,
        )
        

if __name__ == "__main__":
    import asyncio
    chat_module = ChatModule()
    query = InRequest(
        id="1",
        input="What is the capital of France?",
        module="ChatModule",
        stream=True,
    )
    compiled_dr: Graph = compile_to_graph(chat_module.forward)
    scheduler: VScheduler = VScheduler()
    scheduler.register_module(
        module_name="ChatModule",
        compiled_graph=compiled_dr,
        module_instance=chat_module,
    )
    async def run_request(req: InRequest):
        task = scheduler.add_request(req)
        # Wait for the response to ensure session is closed
        resp = await task
        async for chunk in resp.output:
            print(chunk, end="", flush=True)
    asyncio.run(run_request(query))