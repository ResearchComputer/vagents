import os
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, MCPServerArgs, MCPClient, LLM, Session
from vagents.managers import LMManager
from vagents.contrib import summarize
from vagents.executor import compile_to_graph

crawler_mcp: MCPServerArgs = MCPServerArgs(remote_addr="http://localhost:11235/mcp/sse")
local_search_mcp: MCPServerArgs = MCPServerArgs(remote_addr="http://localhost:56146/sse")


# local_search_mcp: MCPServerArgs = MCPServerArgs(
#     command="pipx",
#     args=["run", "mcp-searxng"],
#     envs={"SEARXNG_URL": "http://host.docker.internal:8080"},
# )

def init_step(query: str, **kwargs)-> str:
    """
    You are a helpful assistant in the DeepResearch module.
    """
    return f"You are a helpful assistant. You will be given a query and you will use the tools available to you to answer the query. You should use markdown format (tool name: md) as much as possible. For the `f` parameter, use `fit` when possible. When searching at the beginning, do not use any time_range (use None as parameter if needed). Do not include parameters that are not required. Focus on a general-to-specific process. When use the search tools, make sure the query is keywords instead of full sentence. The tools available to you are: \n\n{kwargs['tools']}. The user's query is: {query}"

def recursive_step(query: str, **kwargs)->None:
    """
    You are a helpful assistant in the DeepResearch module.
    """
    return f"Based on the previous results, you should now focus on using the tools available to you to fine-tune the results."

class DeepResearch(VModule):

    def __init__(self):
        super().__init__(config=VModuleConfig(enable_async=False))
        self.models = LMManager()
        self.client = MCPClient(serverparams=[crawler_mcp, local_search_mcp])
        self.models.add_model(LLM(
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        ))
        self.round_limit = 2

    async def forward(self, query: InRequest) -> OutResponse:
        await self.client.ensure_ready()
        tools = await self.client.list_tools()
        session = Session(query.id)
        session.append({"role": "user", "content": query.input})
        
        init_res = await self.models.invoke(
            init_step,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            query=query.input,
            tools=tools,
        )
        for tool_call in init_res:
            session.append({"role": "assistant", "content": f"I will use the tool {tool_call['function']['name']} with parameters {tool_call['function']['arguments']}"})
            
            result = await self.client.call_tool(
                name = tool_call['function']['name'],
                parameters = tool_call['function']['arguments'],
            )
            session.append({
                "role": "user", 
                "content": f"Here is the result from the tool {tool_call['function']['name']}: {result}"
            })
        
        current_round = 0
        while current_round < self.round_limit:
            print(f"Round {current_round + 1} of {self.round_limit}")
            current_round += 1
            res = await self.models.invoke(
                recursive_step,
                model_name="meta-llama/Llama-3.3-70B-Instruct",
                query=session.history,
                tools=tools,
            )
            for tool_call in res:
                session.append({"role": "assistant", "content": f"I will use the tool {tool_call['function']['name']} with parameters {tool_call['function']['arguments']}"})
                result = await self.client.call_tool(
                    name = tool_call['function']['name'],
                    parameters = tool_call['function']['arguments'],
                )
                session.append({"role": "user", "content": f"Here is the result from the tool {tool_call['function']['name']}: {result}"})
        
        summary = await self.models.invoke(
            summarize,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            query=session.history,
        )
        return OutResponse(
            output=summary,
            session=session.history,
            id=query.id,
            input=query.input,
            module=query.module,
        )
    
    async def cleanup(self, session_id: str) -> None:
        pass  # Placeholder for cleanup logic

if __name__ == "__main__":
    import asyncio
    deep_research = DeepResearch()
    compiled_dr = compile_to_graph(deep_research.forward)
    print(compiled_dr)
    print(f"DeepResearch module initialized with models: {deep_research.models}")
    output = asyncio.run(deep_research.forward(InRequest(
        id="test_query",
        input="Can you tell me who is alan turing?",
        module="DeepResearch"
    )))
    print(f"Output: {output.output}")