from vagents.core import InRequest
from vagents.contrib import DeepResearch
from vagents.executor import GraphExecutor, compile_to_graph, Graph

mcp_configs = [
    {"remote_addr": "http://localhost:11235/mcp/sse"},
    {"remote_addr": "http://localhost:48994/sse"}
]

default_model = "meta-llama/Llama-3.3-70B-Instruct"

if __name__ == "__main__":
    import asyncio
    deep_research = DeepResearch(
        default_model=default_model,
        mcp_configs=mcp_configs
    )
    print(f"DeepResearch module initialized with models: {deep_research.models}")
    request: InRequest = InRequest(
        id="test_query",
        input="Roast Xiaozhe Yao's research, in a cynical and sarcastic tone, as if written by Sir Humphrey Appleby",
        module="DeepResearch",
        additional={"round_limit": 4}
    )
    compiled_graph: Graph = compile_to_graph(deep_research.forward)
    executor = GraphExecutor(
        compiled_graph,
        module_instance=deep_research
    )
    
    output2 = executor.run([request])
    output = asyncio.run(deep_research.forward(request))
    
    print(f"Output: {output.output}")
    print(f"Output2: {output2[0].output}")