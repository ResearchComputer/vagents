import os
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, LLM
from vagents.executor import GraphExecutor, compile_to_graph
from vagents.managers import LMManager
from timeit import default_timer as timer

class ChatModule(VModule):
    def __init__(self):
        super().__init__(config=VModuleConfig(enable_async=False))
        llm = LLM(
            model_name="Qwen/Qwen3-8B",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        )
        self.models = LMManager()
        self.models.add_model(llm)        

    async def forward(self, query: InRequest) -> OutResponse:
        res = await self.models.call("Qwen/Qwen3-8B", messages=[{"role": "user", "content": query.input}])
        
        res2 = await self.models.call("Qwen/Qwen3-8B", [{"role": "user", "content": query.input}])
        return OutResponse(
            output=f"{res}\n\n{res2}",
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
        module="ChatModule"
    )
    start = timer()
    response = asyncio.run(chat_module.forward(query))
    end = timer()
    
    print(f"Time taken: {end - start} seconds")
    compiled_dr = compile_to_graph(chat_module.forward)
    print(f"Compiled graph: {compiled_dr}")

    ge = GraphExecutor(
        compiled_dr, module_instance=chat_module
    )
    start = timer()
    outputs = ge.run(
        [
            InRequest(
                id="test_query",
                input="What is the capital of France?",
                module="ChatModule",
            )
        ]
    )
    end = timer()
    print(f"Time taken for GraphExecutor: {end - start} seconds")