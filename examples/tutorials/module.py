import os
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, LLM
from vagents.executor import GraphExecutor, compile_to_graph

class ChatModule(VModule):
    def __init__(self):
        super().__init__(config=VModuleConfig(enable_async=False))
        self.llm = LLM(
            model_name="Qwen/Qwen3-32B",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        )

    async def forward(self, query: InRequest) -> OutResponse:
        res = await self.llm([{"role": "user", "content": query.input}])
        res = await res.__anext__()
        return OutResponse(
            output=res,
            id=query.id,
            input=query.input,  
            module=query.module,
        )
        

    async def cleanup(self, session_id: str):
        pass

if __name__ == "__main__":
    import asyncio
    chat_module = ChatModule()
    # Example usage
    query = InRequest(
        id="1",
        input="Hello, how are you?",
        module="ChatModule"
    )
    response = asyncio.run(chat_module.forward(query))
    # print(response)
    compiled_dr = compile_to_graph(chat_module.forward)
    # Pass the deep_research instance to GraphExecutor
    ge = GraphExecutor(compiled_dr, module_instance=chat_module)
    outputs = ge.run(
        [
            InRequest(
                id="test_query",
                input="What is the capital of France?",
                module="ChatModule",
            )
        ]
    )
    print(f"outputs: {outputs}")