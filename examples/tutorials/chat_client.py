from vagents.utils import VClient

if __name__ =="__main__":
    client: VClient = VClient(
        base_url="http://localhost:8001",
        api_key="",
    )
    client.register_module(
        path="vagents.contrib.modules.chat:AgentChat",
        force=False,
        mcp_configs = [
            {"remote_addr": "http://localhost:11235/mcp/sse"},
            {"remote_addr": "http://localhost:48994/sse"}
        ]
    )
    
    deep_research_payload_stream = {
        "id": "deep_research_example_001",
        "module": "vagents.contrib.modules.chat:AgentChat",
        "input": "Roast Xiaozhe Yao's Research, in a very cynical and sarcastic tone. Reply in Chinese.",
        "stream": True,
        "additional": {"round_limit": 3}
    }
    print("Calling DeepResearch module (streaming):")
    client.call_response_handler(deep_research_payload_stream)