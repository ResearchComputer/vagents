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
        # yield OutResponse(id=query.id, output=response)