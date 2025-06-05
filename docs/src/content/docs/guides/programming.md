---
title: "Programming with VAgents"
description: A guide in my new Starlight docs site.
---

Programming with VAgents is intuitive and flexible, almost identical to programming with Python. In this tutorial, we will cover the basic semantics and building blocks of VAgents programming.

### Define an LLM Manager

LLMs and their manager is where you define the LLMs you want to use and their configurations.

```python
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
```

### Define LLM Functions

LLM functions are the building blocks of your agent's capabilities. These functions essentially define how you would call the LLMs to perform specific tasks. You can define them as a normal Python function.

```python
def summarize(query: str, **kwargs)-> str:
    """
    You are a helpful assistant.
    """
    return f"Summarize the following text:\n{query}"
```

and then you can invoke them using the LLM manager:

```python
import asyncio

response = asyncio.run(manager.invoke(
    summarize,
    model_name="Qwen/Qwen3-32B",
    query="The Federal Department of Foreign Affairs (FDFA) and ETH Zurich, in collaboration with their international partners, are launching the International Computation and AI Network (ICAIN) at the World Economic Forum (WEF) 2024 in Davos. Its mission is to develop AI technologies that benefit society as a whole, as well as being accessible to all and sustainable, thereby helping to reduce global inequality.",
))
print(f"Response: {response}")
```

The response will be a string containing the summary of the provided text:

```bash
Response: The Federal Department of Foreign Affairs (FDFA) and ETH Zurich, in collaboration with international partners, are launching the International Computation and AI Network (ICAIN) at the World Economic Forum 2024 in Davos. The initiative aims to develop AI technologies that are socially beneficial, accessible, sustainable, and contribute to reducing global inequality.
```

### LLM Functions with Structured Outputs

LLM functions can also return structured outputs. For example, you can define an object type with Pydantic and use it as the return type of your LLM function:

```python
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
```

The response will be a `SummarizeResponse` object containing the summary and rationale:

```bash
type(response): <class '__main__.SummarizeResponse'>
Response: summary="The Federal Department of Foreign Affairs (FDFA) and ETH Zurich, along with international partners, are launching the International Computation and AI Network (ICAIN) at the World Economic Forum (WEF) 2024 in Davos. The network's mission is to develop AI technologies that benefit society, are accessible to all, and are sustainable, with the goal of reducing global inequality." rationale='The summary captures the key elements of the original text: the organizations involved (FDFA, ETH Zurich, and international partners), the event (WEF 2024 in Davos), the initiative (ICAIN), and the mission (developing AI technologies that benefit society, are accessible, sustainable, and help reduce global inequality). The summary is concise while preserving the essential information.'
```

### Invoke Tool Calling with LM Manager

You can also give a function to the `invoke` function of the `LMManager` to provide tools to the LLM. The LLM will then return a structured output that includes the tool calls, which you can then execute.

```python
def search(query: str) -> str:
    return f"[This is a mock search result for query: {query}]"

response = asyncio.run(manager.invoke(
    summarize,
    model_name="Qwen/Qwen3-32B",
    query="What is the International Computation and AI Network (ICAIN)?",
    tools=[search]
))

print(f"{response}")
```

The response will be the tool call:

```bash
[
    {
        'id': 'call_Hr2MMHuBTJa17EcIiHd6nA', 
        'function': {
                'arguments': '{"query": "What is the International Computation and AI Network (ICAIN)?"}', 
                'name': 'search'
            }, 
        'type': 'function'
    }
]
```

:::caution
Be sure to handle the tool calls properly in your code -- you might want a secure environment to execute them, and you should always validate the inputs and outputs of the tool calls to avoid security issues.
:::