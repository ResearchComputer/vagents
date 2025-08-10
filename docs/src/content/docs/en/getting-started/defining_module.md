---
title: "Defining a Module"
description: "Build an AgentModule, register actions, and integrate with the AgentInput/AgentOutput protocols."
sidebar:
  order: 4
---

## What is an AgentModule?

`AgentModule` is a thin async base class for building agent-like modules around an optional `LM`. You implement `async forward(...)`, optionally attach an `LM`, and can expose additional callable actions via the `@agent_action` decorator.

Key behaviors:

- Implement `async forward(...)` in subclasses
- Call an instance like a function to schedule `forward` and get an awaitable Future
- Register actions using `@agent_action`; discovered on init under `instance.actions`
- Optional `LM` helpers: `lm_call(...)` and `await lm_invoke(func, ...)`

## Minimal example

```python
import asyncio
from vagents.core.module import AgentModule, agent_action

class ToyAgent(AgentModule):
    @agent_action
    async def greet(self, name: str) -> str:
        await asyncio.sleep(0)
        return f"hello {name}"

    async def forward(self, x: int) -> int:
        await asyncio.sleep(0)
        return x + 1

# Usage
agent = ToyAgent()
assert "greet" in agent.actions
result = await agent(1)  # schedules forward via internal executor
```

## Defining actions

Annotate instance methods with `@agent_action` to auto-register them as actions on initialization.

```python
class MyAgent(AgentModule):
    @agent_action
    async def summarize(self, text: str) -> str: ...

agent = MyAgent()
await agent.actions["summarize"]("Some text")
```

## Integrating an LM

If you construct your module with an `LM` instance, you can call it via helpers.

```python
from vagents.core import LM

class ChatAgent(AgentModule):
    def __init__(self, lm: LM):
        super().__init__(lm)

    async def forward(self, prompt: str) -> str:
        # Calls self.lm(prompt, ...) through the executor and awaits the result
        text = await self.lm_call(prompt)
        return text

    @agent_action
    async def tool_use(self, data: dict) -> dict:
        # Or invoke a specific LM function with arguments
        return await self.lm_invoke(lambda lm, d: lm.process(d), data)
```

## Using AgentInput/AgentOutput (for packaging and orchestration)

For packages and orchestrators, prefer the standardized protocols:

```python
from vagents.core import AgentInput, AgentOutput

class EchoAgent(AgentModule):
    async def forward(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(input_id=input.id, result={"echo": input.payload})
```

- `AgentInput` carries `payload` and optional `context` for processing
- `AgentOutput` carries a `result` payload or an `error` message

When executed via the package manager, arguments and piped stdin are assembled into an `AgentInput` automatically when your entry point is an `AgentModule` or a function that accepts `AgentInput`.

## Testing tips

- Await `agent(...)` directly; it returns an awaitable Future
- Assert action discovery with `"action_name" in agent.actions`
- Use small awaits (e.g., `await asyncio.sleep(0)`) in tests to yield control
