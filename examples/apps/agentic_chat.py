from vagents.core import InRequest
from vagents.contrib import AgentChat
from vagents.executor import GraphExecutor, compile_to_graph, Graph

mcp_configs = [
    {"remote_addr": "http://localhost:11235/mcp/sse"},
    {"remote_addr": "http://localhost:48994/sse"}
]

default_model = "meta-llama/Llama-3.3-70B-Instruct"

if __name__ == "__main__":
    agent_chat = AgentChat(
        default_model=default_model,
        mcp_configs=mcp_configs
    )
    request: InRequest = InRequest(
        id="test_query",
        input="Roast Xiaozhe Yao's research, in a cynical and sarcastic tone, reply in Chinese",
        module="agent_chat",
        additional={"round_limit": 2}
    )
    compiled_graph: Graph = compile_to_graph(agent_chat.forward)
    print(f"Compiled graph: {compiled_graph}")
    executor = GraphExecutor(
        compiled_graph,
        module_instance=agent_chat
    )
    output = executor.run([request])
    print(f"Output: {output[-1]}")