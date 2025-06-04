import os
import inspect
from typing import List, AsyncGenerator, Dict, Any
from vagents.core import VModule, VModuleConfig, MCPClient, MCPServerArgs, LLM, InRequest, Session
from vagents.managers import LMManager
from vagents.utils import logger

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
    return f"Please finalize the information you have gathered so far. The information you have is: {query}. Based on the actions you have taken: {kwargs['history']}. Return the final result in pure text format with nothing else."

class DeepResearch(VModule):
    def __init__(self,
                 default_model: str="meta-llama/Llama-3.3-70B-Instruct",
                 mcp_configs: List[str]=None
                ) -> None:
        super().__init__(
            config=VModuleConfig(enable_async=False)
        )
        
        self.models = LMManager()
        self.client = MCPClient(serverparams=[
            MCPServerArgs.from_dict(config) for config in mcp_configs] if mcp_configs else []
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

    async def forward(self, query: InRequest) -> AsyncGenerator[Dict[str, Any], None]:
        session: Session = Session(query.id)
        session.append({"role": "user", "content": query.input})

        # Logic from _generate_output_stream is now inlined here
        if "round_limit" in query.additional:
            round_limit = query.additional["round_limit"]
        else:
            round_limit = self.round_limit
        
        await self.client.ensure_ready()
        tools = await self.client.list_tools(hide_tools=self.hide_tools)

        init_res_tool_calls = await self.models.invoke(
            init_step,
            model_name=self.default_model,
            query=query.input,
            tools=tools,
        )
        if init_res_tool_calls:
            for tool_call in init_res_tool_calls:
                tool_name = tool_call['function']['name']
                tool_args = tool_call['function']['arguments']
                
                yield {"type": "data", "content": f"Calling tool: {tool_name}, with arguments: {tool_args}"}
                session.append({"role": "assistant", "content": f"I will use the tool {tool_name} with parameters {tool_args}"})

                tool_result_raw: str = await self.client.call_tool(
                    name=tool_name,
                    parameters=tool_args,
                    override=self.override_parameters
                )
                summarized_tool_result = await self.models.invoke(
                    summarize,
                    model_name=self.default_model,
                    query=tool_result_raw,
                )
                yield {"type": "data", "content": summarized_tool_result}
                session.append({
                    "role": "user", 
                    "content": f"Here is the result from the tool {tool_name}: {summarized_tool_result}"
                })
        
        current_round = 0
        while current_round < round_limit:
            logger.info(f"Round {current_round} / {round_limit} for session {query.id}")
            
            recursive_tool_calls = await self.models.invoke(
                recursive_step,
                model_name=self.default_model,
                query=str(session.history),
                tools=tools,
            )
            if recursive_tool_calls:
                for tool_call in recursive_tool_calls:
                    tool_name = tool_call['function']['name']
                    tool_args = tool_call['function']['arguments']

                    yield {"type": "data", "content": f"Calling tool: {tool_name}, with arguments: {tool_args}"}
                    session.append({"role": "assistant", "content": f"I will use the tool {tool_name} with parameters {tool_args}"})
                    
                    tool_result_raw = await self.client.call_tool(
                        name=tool_name,
                        parameters=tool_args,
                        override=self.override_parameters
                    )
                    summarized_tool_result = await self.models.invoke(
                        summarize,
                        model_name=self.default_model,
                        query=tool_result_raw,
                    )
                    yield {"type": "data", "content": summarized_tool_result}
                    session.append({"role": "user", "content": f"Here is the result from the tool {tool_name}: {summarized_tool_result}"})
                
                if current_round < round_limit -1 : 
                     session.append({"role": "assistant", "content": "Now I will proceed to the next round."})
            else:
                logger.info(f"Skip round {current_round} / {round_limit} for session {query.id}")
                if current_round < round_limit -1: 
                    session.append({"role": "assistant", "content": "No actions taken in this round. Proceeding to the next round."})
            current_round += 1
        
        final_summary_obj = await self.models.invoke(
            finalize,
            model_name="Qwen/Qwen3-32B",
            query=query.input,
            history=str(session.history),
        )

        if inspect.isasyncgen(final_summary_obj):
            async for chunk in final_summary_obj:
                yield {"type": "data", "content": chunk}
        elif isinstance(final_summary_obj, str):
            yield {"type": "data", "content": final_summary_obj}
        elif final_summary_obj is not None:
            logger.warning(f"Unexpected type from finalize invoke for session {query.id}: {type(final_summary_obj)}. Converting to string.")
            yield {"type": "data", "content": str(final_summary_obj)}

        # Yield final metadata as the last item
        yield {
            "type": "metadata",
            "content": {
                "session_history": session.history,
                "id": query.id,
                "input": query.input,
                "module": query.module,
            }
        }
    
    async def cleanup(self, session_id: str) -> None:
        logger.info(f"Cleanup called for session {session_id} in DeepResearch module.")
        pass