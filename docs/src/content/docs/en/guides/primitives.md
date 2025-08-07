---
title: "Programming Primitives"
description: "The fundamental building blocks of programming with vagents."
sidebar:
  order: 2
---

# LLM Invocations

LLM invocations in vagents are handled through the `LM` class, which provides a simple and consistent interface for interacting with language models. The framework supports both text-only and multimodal interactions.

## Basic Text LLM Usage

### Creating an LM Instance

```python
from vagents.core import LM

# Create an LM instance with auto model selection
lm = LM(name="@auto")

# Or specify a particular model
lm = LM(
    name="meta-llama/Llama-3.2-90B-Vision-Instruct",
    base_url="http://localhost:8000",
    api_key="your-api-key-here"
)
```

### Defining Prompt Functions

Prompt functions are regular Python functions that return a list of messages in OpenAI chat format:

```python
def write_story(query: str) -> list:
    """Generate a story based on the given query."""
    return [{"role": "user", "content": "write a story about " + query}]
```

### Invoking the LLM

Use the `invoke` method to call your prompt function with the LM:

```python
import asyncio

async def main():
    lm = LM(name="@auto")
    description = await lm.invoke(write_story, "a brave knight and a dragon")
    print(description)
asyncio.run(main())
```

### Concurrent Invocations

For better performance when making multiple requests, you can execute them concurrently:

```python
async def concurrent_example():
    lm = LM(name="@auto")

    # Start multiple requests concurrently
    future1 = lm(messages=[{"role": "user", "content": "Hello, how are you? in one word"}])
    future2 = lm(messages=[{"role": "user", "content": "What's the weather like? in one word"}])
    future3 = lm(messages=[{"role": "user", "content": "Tell me a joke in one word"}])

    # Wait for all to complete
    response1, response2, response3 = await asyncio.gather(future1, future2, future3)

    print("Response 1:", response1)
    print("Response 2:", response2)
    print("Response 3:", response3)
```

## Multimodal LLM Usage

For multimodal interactions (text + images), use the `@multimodal` decorator:

```python
from PIL import Image
from vagents.core import multimodal, LM

@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """Describe the contents of an image frame."""
    return "Describing frame at index."

async def multimodal_example():
    # Load an image
    frame = Image.open("path/to/image.jpg")

    # Use a vision-capable model
    model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

    # Invoke with image and additional parameters
    description = await model.invoke(
        narrate_frame,
        frame=frame,
        temperature=0.7,
        max_tokens=100,
        stream=False
    )
    print(description)
```

## Configuration

### Environment Variables

You can configure the LM instance using environment variables:

- `VAGENTS_LM_BASE_URL`: The base URL for the LM API (default: `http://localhost:8000`)
- `VAGENTS_LM_API_KEY`: The API key for authentication (default: `your-api-key-here`)

### Supported Parameters

When invoking LLMs, you can pass the following optional parameters:

- `temperature`: Controls randomness in the output
- `top_p`: Controls nucleus sampling
- `max_tokens`: Maximum number of tokens to generate
- `stream`: Whether to stream the response
- `stop`: Stop sequences for generation
- `n`: Number of completions to generate
- `presence_penalty`: Penalty for new tokens based on presence
- `frequency_penalty`: Penalty for new tokens based on frequency

Example with parameters:

```python
result = await lm.invoke(
    write_story,
    "a magical forest",
    temperature=0.8,
    max_tokens=200,
    stop=["\n\n"]
)
```
