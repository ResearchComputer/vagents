import os
from vagents.core import LLM
from vagents.managers import LMManager

llm = LLM(
    model_name="Qwen/Qwen3-32B",
    base_url=os.environ.get("RC_API_BASE", ""),
    api_key=os.environ.get("RC_API_KEY", ""),
)

manager: LMManager = LMManager()
manager.add_model(llm)

def summarize(query: str, **kwargs)-> str:
    """
    You are a helpful assistant.
    """
    return f"Summarize the following text:\n{query}"

import asyncio

response = asyncio.run(manager.invoke(
    summarize,
    model_name="Qwen/Qwen3-32B",
    query="The Federal Department of Foreign Affairs (FDFA) and ETH Zurich, in collaboration with their international partners, are launching the International Computation and AI Network (ICAIN) at the World Economic Forum (WEF) 2024 in Davos. Its mission is to develop AI technologies that benefit society as a whole, as well as being accessible to all and sustainable, thereby helping to reduce global inequality.",
))
print(f"Response: {response}")

from pydantic import BaseModel

class SummarizeResponse(BaseModel):
    summary: str
    rationale: str
    
def summarize_with_rationale(query: str, **kwargs) -> SummarizeResponse:
    """
    You are a helpful assistant.
    """
    return f"Summarize the following text:\n{query}"

response = asyncio.run(manager.invoke(
    summarize_with_rationale,
    model_name="Qwen/Qwen3-32B",
    query="The Federal Department of Foreign Affairs (FDFA) and ETH Zurich, in collaboration with their international partners, are launching the International Computation and AI Network (ICAIN) at the World Economic Forum (WEF) 2024 in Davos. Its mission is to develop AI technologies that benefit society as a whole, as well as being accessible to all and sustainable, thereby helping to reduce global inequality.",
))
print(f"type(response): {type(response)}")
print(f"Response: {response}")

def search(query: str) -> str:
    return f"[This is a mock search result for query: {query}]"

response = asyncio.run(manager.invoke(
    summarize,
    model_name="Qwen/Qwen3-32B",
    query="What is the International Computation and AI Network (ICAIN)?",
    tools=[search]
))

print(f"Response: {response}")