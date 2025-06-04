from vagents.core import InRequest
from vagents.contrib import LocalResearch
from vagents.utils import pprint_markdown
default_model = "Qwen/Qwen3-32B"

mcp_configs = [
    {"remote_addr": "http://localhost:11235/mcp/sse"},
    {"remote_addr": "http://localhost:48994/sse"}
]


if __name__ == "__main__":
    import asyncio
    local_research: LocalResearch = LocalResearch(
        default_model=default_model,
        mcp_configs=mcp_configs
    )
    request: InRequest = InRequest(
        id="test_query",
        input="Tell me about some recent advancements made by Xiaozhe Yao",
        module="DeepResearch",
        additional={"round_limit": 2}
    )
    res = asyncio.run(local_research.forward(request))
    
    pprint_markdown(res.output)