from vagents.utils import VClient

if __name__ =="__main__":
    client: VClient = VClient(
        base_url="http://localhost:8001",
        api_key="",
    )
    client.register_module(
        path="vagents.contrib.modules.deep_research:DeepResearch",
        force=False,
        mcp_configs = [
            {"remote_addr": "http://localhost:11235/mcp/sse"},
            {"remote_addr": "http://localhost:48994/sse"}
        ]
    )

    deep_research_payload = {
        "id": "deep_research_example_001",
        "module": "vagents.contrib.modules.deep_research:DeepResearch",
        "input": "What are the latest advancements in AI?",
        "stream": False,
        "additional": {"round_limit": 2}
    }
    print("\\nCalling DeepResearch module:")
    client.call_response_handler(deep_research_payload)

    # Example call for streaming response (if supported by the module)
    # deep_research_payload_stream = {
    #     "id": "deep_research_example_002",
    #     "module": "vagents.contrib.modules.deep_research:DeepResearch",
    #     "input": "Tell me a short story about a robot.",
    #     "stream": True,
    #     "additional": {}
    # }
    # print("\\nCalling DeepResearch module (streaming):")
    # client.call_response_handler(deep_research_payload_stream)