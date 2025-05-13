from typing import List
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse
from vagents.executor import GraphExecutor, compile_to_graph


def init_session(query_id: str, tools: List[dict]):
    return []  # Changed to return a list


class DeepResearch(VModule):
    def __init__(self):
        super().__init__(config=VModuleConfig(enable_async=False))
        self.llm = lambda x: x
        self.client = None

    def forward(self, query: InRequest) -> OutResponse:
        ROUND_LIMIT = 1
        current_round = 0
        self.client.ensure_ready()

        tools = self.client.list_tools()
        session = init_session(query.id, tools)
        session.append(
            {
                "role": "user",
                "content": f"My query is: {query.input}. Please use the tools available to you as the next step to answer my query.",
            }
        )
        while current_round < ROUND_LIMIT:
            tool_use = session.action(
                self.llm, tools=tools
            )  # Assuming session.action exists and works as expected
            current_round += 1
            if tool_use.status == "abnormal":
                break
            tool_use = tool_use.content
            tool_result = self.client.call_tool(
                name=tool_use["name"],
                parameters=tool_use["parameters"],
            )
        # Placeholder for actual answer processing
        final_answer = "Processed answer based on tool results and session."
        return OutResponse(
            id=query.id, input=query.input, module="DeepResearch", answer=final_answer
        )

    async def cleanup(self, session_id: str):
        pass


if __name__ == "__main__":
    deep_research = DeepResearch()
    compiled_dr = compile_to_graph(deep_research.forward)
    # Pass the deep_research instance to GraphExecutor
    ge = GraphExecutor(compiled_dr, module_instance=deep_research)
    ge.run(
        [
            InRequest(
                id="test_query",
                input="What is the capital of France?",
                module="DeepResearch",
            )
        ]
    )
