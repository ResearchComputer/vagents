---
title: "定义模块"
description: "构建 AgentModule，注册动作，并与 AgentInput/AgentOutput 协议集成。"
sidebar:
  order: 2
---

## 什么是 AgentModule？

`AgentModule` 是一个用于围绕可选 `LM` 构建异步模块的轻量级基类。你需要在子类中实现 `async forward(...)`，可选地在构造时注入 `LM`，并通过 `@agent_action` 装饰器暴露额外的可调用动作。

要点：

- 在子类中实现 `async forward(...)`
- 直接调用实例即可调度 `forward`，返回可等待的 Future
- 使用 `@agent_action` 注册动作；在初始化时会自动发现并填充到 `instance.actions`
- 可选 `LM` 辅助方法：`lm_call(...)` 和 `await lm_invoke(func, ...)`

## 最小示例

```python
import asyncio
from vagents.core.module import AgentModule, agent_action

class ToyAgent(AgentModule):
    @agent_action
    async def greet(self, name: str) -> str:
        await asyncio.sleep(0)
        return "hello {name}"

    async def forward(self, x: int) -> int:
        await asyncio.sleep(0)
        return x + 1

# 用法
agent = ToyAgent()
assert "greet" in agent.actions
result = await agent(1)  # 通过内部执行器调度 forward
```

## 定义动作

给实例方法添加 `@agent_action` 装饰器，即可在初始化时自动注册为动作。

```python
class MyAgent(AgentModule):
    @agent_action
    async def summarize(self, text: str) -> str: ...

agent = MyAgent()
await agent.actions["summarize"]("Some text")
```

## 集成 LM

若在构造函数中注入 `LM` 实例，可以通过辅助方法发起调用。

```python
from vagents.core import LM

class ChatAgent(AgentModule):
    def __init__(self, lm: LM):
        super().__init__(lm)

    async def forward(self, prompt: str) -> str:
        # 通过执行器调用 self.lm(prompt, ...)，并等待结果
        text = await self.lm_call(prompt)
        return text

    @agent_action
    async def tool_use(self, data: dict) -> dict:
        # 以函数形式调用 LM，并传入参数
        return await self.lm_invoke(lambda lm, d: lm.process(d), data)
```

## 使用 AgentInput/AgentOutput（用于打包与编排）

在包与编排场景中，优先使用标准协议：

```python
from vagents.core import AgentInput, AgentOutput

class EchoAgent(AgentModule):
    async def forward(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(input_id=input.id, result={"echo": input.payload})
```

- `AgentInput` 携带用于处理的 `payload` 和可选 `context`
- `AgentOutput` 携带 `result` 负载或 `error` 信息

当通过包管理器执行时，若入口是 `AgentModule` 子类，或是接受 `AgentInput` 的函数，包管理器会从 CLI 参数与标准输入自动组装 `AgentInput`，并在可能时将返回值封装/转换为 `AgentOutput`。

## 测试提示

- 直接 `await agent(...)`，其返回值为可等待的 Future
- 用 `"action_name" in agent.actions` 断言你的动作已被自动发现
- 测试中可使用 `await asyncio.sleep(0)` 等方式让出事件循环
