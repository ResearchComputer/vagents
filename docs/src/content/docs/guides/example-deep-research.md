---
title: "Example: Deep Research"
description: A guide in my new Starlight docs site.
---

## Prerequisites

Make sure you have `docker` installed and running. The following example also relies on an external LLM service. Please set the following environment variables:

```bash
export RC_API_BASE="https://api.swissai.cscs.ch/v1"
export RC_API_KEY="sk-rc-[...]"
```

Then, please clone the `vagents` repository:

```bash
git clone git@github.com:vagents-ai/vagents.git && cd vagents
pip install -e .
```

### Run the Search Service

We need to run a search service that can fetch content from the internet. We use two Docker containers: one for search ([searxng](https://github.com/searxng/searxng)) and one for crawling ([crawl4ai](https://docs.crawl4ai.com/)).

```bash
bash tools/background_tasks/searxng/start_crawl4ai.sh
bash tools/background_tasks/searxng/start_searxng.sh
```

These two commands will start the search and crawling services in the background, inside Docker containers. They will listen on ports 8080 and 11235, respectively. You can check if they are running by executing the following command:

```bash
docker ps
```

You should see output similar to this, indicating two running containers:

```bash
CONTAINER ID   IMAGE                                 COMMAND                  CREATED        STATUS                      PORTS                                                     NAMES
1a05c4cae463   unclecode/crawl4ai:latest             "supervisord -c supe…"   25 hours ago   Up 25 hours (healthy)       6379/tcp, 0.0.0.0:11235->11235/tcp, :::11235->11235/tcp   crawl4ai
5fc145637bd8   searxng/searxng:latest                "/usr/local/searxng/…"   25 hours ago   Up 25 hours (healthy)       0.0.0.0:8080->8080/tcp, :::8080->8080/tcp                 elegant_williams
```

### Run the Deep Research Module with MCP

We will use [Model Context Protocol](https://modelcontextprotocol.io/introduction) to communicate with the search service.

```python
from vagents.core import InRequest
from vagents.contrib import LocalResearch
from vagents.utils import pprint_markdown

default_model = "Qwen/Qwen3-32B"

mcp_configs = [
    {"remote_addr": "http://localhost:11235/mcp/sse"},
    {"command": "pipx", "args": ["run", "mcp-searxng"], "envs": {"SEARXNG_URL": "http://host.docker.internal:8080"}}
]

if __name__ == "__main__":
    import asyncio
    local_research: LocalResearch = LocalResearch(
        default_model=default_model,
        mcp_configs=mcp_configs
    )
    request: InRequest = InRequest(
        id="test_query",
        input="Tell me something about Swiss AI Initiative.",
        module="DeepResearch",
        additional={"round_limit": 2}
    )
    res = asyncio.run(local_research.forward(request))
    
    pprint_markdown(res.output)
```

Here, we import the `LocalResearch` module from `vagents.contrib`. We set up the default model we want to use for this module and define a few MCP configurations. Vagents supports both remote and local MCP configurations: 1) For remote configurations, we only specify the address. 2) For local configurations, we specify the command to run and the environment variables to set. In this case, Vagents will run the command in a Docker container and connect to the service via the HTTP protocol.

:::tip
Since Vagents always runs MCP servers in a Docker container and communicates with them via HTTP, you can easily reuse these MCP servers. For example, in the code above, Vagents starts the `mcp-searxng` server in a Docker container and connects to it via HTTP. Once the server is running and you obtain the port it is listening on (from the `docker ps` command), you can use it in other Vagents modules or even in your own code. For instance, you can specify the `remote_addr` in the `mcp_configs` to connect to the running MCP server.
:::

### Local Research Module

For reference, here is the code for the `LocalResearch` module:

```python

import os
import json
from vagents.utils import logger
from vagents.managers import LMManager
from typing import AsyncGenerator, List
from vagents.contrib.modules.utils import get_current_date
from vagents.contrib.functions import summarize, finalize
from vagents.core import VModule, VModuleConfig, MCPClient, MCPServerArgs, LLM, InRequest, Session, OutResponse

from pydantic import BaseModel

class Query(BaseModel):
    query: str
    rationale: str

class URLs(BaseModel):
    urls: List[str]

class FollowUpQuery(BaseModel):
    knowledge_gap: str
    follow_up_query: str

def generate_query(query:str, **kwargs) -> Query:
    """
    Your goal is to generate a targeted web search query.
    <CONTEXT>
    Current date: {current_date}
    Please ensure your queries account for the most current information available as of this date.
    </CONTEXT>
    <FORMAT>
    Format your response as a JSON object with ALL three of these exact keys:
    - "query": The actual search query string, should be concise and relevant, suitable for web search
    - "rationale": Brief explanation of why this query is relevant
    </FORMAT>
    <EXAMPLE>
    Example output:
    {{
        "query": "machine learning transformer architecture explained",
        "rationale": "Understanding the fundamental structure of transformer models"
    }}
    </EXAMPLE>

    Provide your response in JSON format without anything else.
    """
    current_date = get_current_date()
    return f"Current date: {current_date}\n\nQuery:{query}\n\nGenerate a query for web search."

def parse_urls(query: str, **kwargs) -> URLs:
    """
    Your goal is to extract URLs from the provided text.
    <FORMAT>
    Format your response as a JSON object with a single key:
    - "urls": A list of URLs extracted from the text
    </FORMAT>
    <EXAMPLE>
    Example output:
    {{
        "urls": [
            "https://example.com/article1",
            "https://example.com/article2"
        ]
    }}
    </EXAMPLE>

    Provide your response in JSON format without anything else.
    """
    return f"Extract URLs from the following text: {query}\n\nReturn a JSON object with a single key 'urls' containing a list of URLs."

def reflection(query: str, **kwargs) -> FollowUpQuery:
    """
    You are an expert research assistant analyzing a summary about {research_topic}.
    <GOAL>
    1. Identify knowledge gaps or areas that need deeper exploration
    2. Generate a follow-up question that would help expand your understanding
    3. Focus on technical details, implementation specifics, or emerging trends that weren't fully covered
    </GOAL>

    <REQUIREMENTS>
    Ensure the follow-up question is self-contained and includes necessary context for web search.
    </REQUIREMENTS>

    <FORMAT>
    Format your response as a JSON object with these exact keys:
    - knowledge_gap: Describe what information is missing or needs clarification
    - follow_up_query: Write a specific question to address this gap
    </FORMAT>

    <Task>
    Reflect carefully on the summary to identify knowledge gaps and produce a follow-up query. Then, produce your output following this JSON format:
    {{
        "knowledge_gap": "The summary lacks information about performance metrics and benchmarks",
        "follow_up_query": "What are typical performance benchmarks and metrics used to evaluate transformer models in NLP tasks?"
    }}
    </Task>

    Provide your analysis in JSON format:
    """
    return f"Reflect on our existing knowledge: \n\n{query}\n\n And now identify a knowledge gap and generate a follow-up web search query"

class LocalResearch(VModule):
    def __init__(self, default_model: str = "meta-llama/Llama-3.3-70B-Instruct", mcp_configs: List[str]=None) -> None:
        super().__init__(config=VModuleConfig())
        self.default_model = default_model
        self.models = LMManager()
        self.models.add_model(LLM(
            model_name=self.default_model,
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        ))
        self.client = MCPClient(serverparams=[
            MCPServerArgs.from_dict(config) for config in mcp_configs] if mcp_configs else []
        )
        self.round_limit = 2

    async def forward(self, query: InRequest) -> AsyncGenerator[OutResponse, None]:
        await self.client.ensure_ready()
        session: Session = Session(query.id)
        queries = await self.models.invoke(
            generate_query,
            model_name=self.default_model,
            query=query.input,
            **query.additional
        )
        
        tool_result_raw: str = await self.client.call_tool(
            name="search",
            parameters={
                "query": queries.query
            }
        )
        urls = await self.models.invoke(
            parse_urls,
            model_name=self.default_model,
            query=tool_result_raw,
            **query.additional
        )
        current_knowledge = ""
        for url in urls.urls:
            contents: str = await self.client.call_tool(
                name="md",
                parameters={
                    "c": "0",
                    "url": url
                }
            )
            contents = json.loads(contents)
            contents = contents['markdown']
            contents = await self.models.invoke(
                summarize,
                model_name=self.default_model,
                query=contents,
                **query.additional
            )
            current_knowledge += contents + "\n\n"
        
        for i in range(query.additional.get("round_limit", self.round_limit)):
            follow_up_query = await self.models.invoke(
                reflection,
                model_name=self.default_model,
                query=current_knowledge,
                **query.additional
            )
            print(f"Searching for follow-up query: {follow_up_query.follow_up_query}")
            tool_result_raw = await self.client.call_tool(
                name="search",
                parameters={
                    "query": follow_up_query.follow_up_query
                }
            )
            urls = await self.models.invoke(
                parse_urls,
                model_name=self.default_model,
                query=tool_result_raw,
                **query.additional
            )
            for url in urls.urls:
                contents: str = await self.client.call_tool(
                    name="md",
                    parameters={
                        "c": "0",
                        "url": url
                    }
                )
                contents = json.loads(contents)
                contents = contents['markdown']
                contents = await self.models.invoke(
                    summarize,
                    model_name=self.default_model,
                    query=contents,
                    **query.additional
                )
                current_knowledge += contents + "\n\n"
        
        final_answer = await self.models.invoke(
            finalize,
            model_name=self.default_model,
            query=query.input,
            knowledge=current_knowledge,
            **query.additional
        )
        return OutResponse(
            id=query.id,
            output=final_answer,
            module="local_research",
            input=query.input,
        )
```