---
title: "Compose a Module"
description: A guide in my new Starlight docs site.
---

A module in vagents is a collection of LLM functions and tools, as well as the workflow that uses them. You can compose a module by defining the LLM functions and tools you want to use, and then creating a workflow that uses them. Here's an example of how to compose a simple RAG module that fetches content from wikipedia and uses it to answer questions:

### Step 1: Define Retrieval Function

Here we implement a simple function to retrieve content from Wikipedia based on a keyword search.

```python
import os
import json
from typing import AsyncGenerator
from vagents.managers import LMManager
from vagents.core import VModule, VModuleConfig, InRequest, OutResponse, LLM
from vagents.utils import pprint_markdown

def search_wikipedia(keyword) -> str:
    """
    Function to search Wikipedia for a keyword.
    """
    import wikipedia
    try:
        results = wikipedia.search(keyword)
        if results:
            summaries = []
            for res in results:
                try:
                    summary = wikipedia.summary(res, sentences=5)
                    summaries.append(summary)
                except Exception as e:
                    pass
            return "\n\n".join(summaries)
        else:
            return f"No results found for '{keyword}'."
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"
```

### Step 2: Define the LLM Function

We then define two LLM functions: one for generating the query keyword from the user input, and another for summarizing the Wikipedia content:

```python
def generate_query(query: str, **kwargs) -> str:
    """
    Generate a search query based on the input text. The query will be sent to wikipedia.
    """
    return f"Generate a concise search query for the following query: {query}. Return the query only, without any additional text."

def summary(query: str, **kwargs) -> str:
    """
    Generate a summary for the given query.
    """
    return f"Summarize the following text:\n{query}"
```

### Step 3: Create the Module

We can then create a module that uses these functions and the Wikipedia retrieval function:

```python
class RAGModule(VModule):
    def __init__(self, default_model: str = "meta-llama/Llama-3.3-70B-Instruct") -> None:
        super().__init__(config=VModuleConfig())
        self.default_model = default_model
        self.models = LMManager()
        self.models.add_model(LLM(
            model_name=self.default_model,
            base_url=os.environ.get("RC_API_BASE", ""),
            api_key=os.environ.get("RC_API_KEY", ""),
        ))
    
    async def forward(self, query: InRequest) -> AsyncGenerator[OutResponse, None]:
        search_query = await  self.models.invoke(
            generate_query,
            model_name=self.default_model,
            query=query.input,
            tools=[search_wikipedia],
            **query.additional
        )
        assert search_query[0]['function']['name'] == "search_wikipedia", \
            f"Expected function name 'search_wikipedia', got {search_query[0]['function']['name']}"
        search_query = json.loads(search_query[0]['function']['arguments'])['keyword']
        search_result = search_wikipedia(search_query)
        
        summary_result = await self.models.invoke(
            summary,
            model_name=self.default_model,
            query=search_result,
            **query.additional
        )
        return OutResponse(
            id=query.id,
            input=query.input,
            output=summary_result,
            module=query.module,
            additional=query.additional
        )
```

### Step 4: Use the Module

You can now use this module in your application. Here's an example of how to use it:

```python
if __name__=="__main__":
    import asyncio
    req = InRequest(
        id="test",
        input="Who is Alan Turing?",
        module="RAGModule",
    )
    rag: RAGModule = RAGModule(
        default_model="meta-llama/Llama-3.3-70B-Instruct"
    )
    res = asyncio.run(rag(req))
    pprint_markdown(res.output)
```