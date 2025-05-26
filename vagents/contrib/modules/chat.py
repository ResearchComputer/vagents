import os
from typing import List, AsyncGenerator
from vagents.managers import LMManager
from vagents.core import VModule, VModuleConfig, MCPClient, MCPServerArgs, LLM, InRequest, OutResponse, Session

def init_step(query: str, **kwargs)-> str:
    """
    You are a helpful assistant in the DeepResearch module.
    """
    return f"You are a helpful assistant. You will be given a query and you will use the tools available to you to answer the query. You should use markdown format (tool name: md) as much as possible. For the `f` parameter, use `fit` when possible. When searching at the beginning, do not use any time_range (use None as parameter if needed). Do not include parameters that are not required. Focus on a general-to-specific process. When use the search tools, make sure the query is keywords instead of full sentence. The tools available to you are: \n\n{kwargs['tools']}. Please start with the `search` tool to gather some hyperlinks. The user's query is: {query}"

def recursive_step(query: str, **kwargs)->None:
    """
    You are a helpful assistant in the DeepResearch module.
    """
    return f"Based on the previous result: {query}, please use tools available to you to further refine the results. Try to visit the hyperlinks in the previous result. You can also use the tools to search for more information."

def summarize(query: str, **kwargs)->str:
    """
    You are a helpful assistant in the DeepResearch module.
    """
    return f"Please summarize the information you have gathered so far. Please summarize the information while keeping all hyperlinks. The information you have is: {query}. Return the summary in markdown format with nothing else."

def finalize(query: str, **kwargs) ->str:
    """
    You are a helpful assistant in the DeepResearch module.
    """
    return f"Please finalize the information you have gathered so far. The information you have is: {query}. Based on the actions you have taken: {kwargs['history']}. Return the final result in markdown format. Show images in markdown format."

class AgentChat(VModule):

    def __init__(self,
                 default_model: str="meta-llama/Llama-3.3-70B-Instruct",
                 mcp_configs: List[str]=None
                ) -> None:
        
        super().__init__(config=VModuleConfig())
        
        self.models = LMManager()
        self.client = MCPClient(
            serverparams=[MCPServerArgs.from_dict(config) for config in mcp_configs] if mcp_configs else []
        )
        self.default_model = default_model
        
        self.models.add_model(LLM(
            model_name=self.default_model,
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        ))

        self.models.add_model(LLM(
            model_name="Qwen/Qwen3-32B",
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        ))

        self.round_limit = 2
        self.override_parameters = {
            'md': {
                'c': "0",
            }
        }
        self.hide_tools = ['pdf', 'html', 'screenshot', 'execute_js']

    async def forward(self, query: InRequest) -> AsyncGenerator[OutResponse, None]:
        if "round_limit" in query.additional:
            round_limit = query.additional["round_limit"]
        else:
            round_limit = self.round_limit
        
        await self.client.ensure_ready()
        
        tools = await self.client.list_tools(hide_tools=self.hide_tools)
        
        print(f"Tools available: {[tool.name for tool in tools]}")
        
        session: Session = Session(query.id)
        session.append({"role": "user", "content": query.input})

        init_res = await self.models.invoke(
            init_step,
            model_name=self.default_model,
            query=query.input,
            tools=tools,
        )
        for tool_call in init_res:
            session.append({"role": "assistant", "content": f"I will use the tool {tool_call['function']['name']} with parameters {tool_call['function']['arguments']}"})
            yield {"type": "tool_call", "name": tool_call['function']['name'], "arguments": tool_call['function']['arguments']}
            
            result: str = await self.client.call_tool(
                name = tool_call['function']['name'],
                parameters = tool_call['function']['arguments'],
                override = self.override_parameters
            )
            result = await self.models.invoke(
                summarize,
                model_name=self.default_model,
                query=result,
            )
            yield {"type": "tool_result", "name": tool_call['function']['name'], "result": result}
            
            session.append({
                "role": "user", 
                "content": f"Here is the result from the tool {tool_call['function']['name']}: {result}"
            })
        
        print("DEBUG: Before while loop in AgentChat.forward") # Diagnostic print
        current_round = 0
        while current_round < round_limit:
            print(f"DEBUG: Top of while loop, current_round = {current_round}") # Diagnostic print
            print(f"Round {current_round} / {round_limit}")
            res = await self.models.invoke(
                recursive_step,
                model_name=self.default_model,
                query=str(session.history),
                tools=tools,
            )
            if res:
                for tool_call in res:
                    session.append({"role": "assistant", "content": f"I will use the tool {tool_call['function']['name']} with parameters {tool_call['function']['arguments']}"})
                    yield {"type": "tool_call", "name": tool_call['function']['name'], "arguments": tool_call['function']['arguments']}
                    try:
                        result = await self.client.call_tool(
                            name = tool_call['function']['name'],
                            parameters = tool_call['function']['arguments'],
                            override = self.override_parameters
                        )
                        result = await self.models.invoke(
                            summarize,
                            model_name=self.default_model,
                            query=result,
                        )
                        yield {"type": "tool_result", "name": tool_call['function']['name'], "result": result}
                        
                        session.append({"role": "user", "content": f"Here is the result from the tool {tool_call['function']['name']}: {result}"})
                    except Exception as e:
                        print(f"Error calling tool {tool_call['function']['name']}: {e}")
                        session.append({"role": "assistant", "content": f"An error occurred while calling the tool {tool_call['function']['name']}: {e}"})
                        yield {"type": "tool_result", "name": tool_call['function']['name'], "result": f"An error occurred while calling the tool: {e}"}
                    
                if current_round < round_limit:
                    session.append({"role": "assistant", "content": f"Now I will proceed to the next round."})
            else:
                print(f"DEBUG: 'res' is empty/None for round {current_round}") # Diagnostic print
                print(f"Skip round {current_round} / {self.round_limit}")
                session.append({"role": "assistant", "content": f"Now I will proceed to the next round."})
            current_round += 1
        
        print("DEBUG: After while loop, before final_answer") # Diagnostic print
        # Use the helper function for streaming the final summary
        final_answer = await self.models.invoke(
            finalize,
            model_name="Qwen/Qwen3-32B",
            query=query.input,
            history=str(session.history),
        )
        print(f"final answer: {final_answer}")  # Diagnostic print
        yield OutResponse(
            output=final_answer,
            session=session.history,
            id=query.id,
            input=query.input,
            module=query.module,
        )
    
    async def cleanup(self, session_id: str) -> None:
        pass