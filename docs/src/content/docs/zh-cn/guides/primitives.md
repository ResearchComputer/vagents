---
title: "编程原语"
description: "使用 vagents 编程的基本构建块。"
sidebar:
  order: 2
---

# LLM 调用

在 vagents 中，LLM 调用通过 `LM` 类处理，它为与语言模型交互提供了简单一致的接口。框架支持纯文本和多模态交互。

## 基本文本 LLM 使用

### 创建 LM 实例

```python
from vagents.core import LM

# 使用自动模型选择创建 LM 实例
lm = LM(name="@auto")

# 或指定特定模型
lm = LM(
    name="meta-llama/Llama-3.2-90B-Vision-Instruct",
    base_url="http://localhost:8000",
    api_key="your-api-key-here"
)
```

### 定义提示函数

提示函数是返回 OpenAI 聊天格式消息列表的常规 Python 函数：

```python
def write_story(query: str) -> list:
    """根据给定查询生成故事。"""
    return [{"role": "user", "content": "写一个关于" + query + "的故事"}]
```

### 调用 LLM

使用 `invoke` 方法通过 LM 调用您的提示函数：

```python
import asyncio

async def main():
    lm = LM(name="@auto")
    description = await lm.invoke(write_story, "勇敢的骑士和龙")
    print(description)
asyncio.run(main())
```

### 并发调用

为了在发出多个请求时获得更好的性能，您可以并发执行它们：

```python
async def concurrent_example():
    lm = LM(name="@auto")

    # 并发启动多个请求
    future1 = lm(messages=[{"role": "user", "content": "你好，你怎么样？用一个词回答"}])
    future2 = lm(messages=[{"role": "user", "content": "天气怎么样？用一个词回答"}])
    future3 = lm(messages=[{"role": "user", "content": "讲个笑话，用一个词"}])

    # 等待所有请求完成
    response1, response2, response3 = await asyncio.gather(future1, future2, future3)

    print("响应 1:", response1)
    print("响应 2:", response2)
    print("响应 3:", response3)
```

## 多模态 LLM 使用

对于多模态交互（文本 + 图像），使用 `@multimodal` 装饰器：

```python
from PIL import Image
from vagents.core import multimodal, LM

@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """描述图像帧的内容。"""
    return "正在描述索引处的帧。"

async def multimodal_example():
    # 加载图像
    frame = Image.open("path/to/image.jpg")

    # 使用支持视觉的模型
    model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

    # 使用图像和附加参数调用
    description = await model.invoke(
        narrate_frame,
        frame=frame,
        temperature=0.7,
        max_tokens=100,
        stream=False
    )
    print(description)
```

## 配置

### 环境变量

您可以使用环境变量配置 LM 实例：

- `VAGENTS_LM_BASE_URL`：LM API 的基础 URL（默认：`http://localhost:8000`）
- `VAGENTS_LM_API_KEY`：用于身份验证的 API 密钥（默认：`your-api-key-here`）

### 支持的参数

调用 LLM 时，您可以传递以下可选参数：

- `temperature`：控制输出的随机性
- `top_p`：控制核采样
- `max_tokens`：生成的最大令牌数
- `stream`：是否流式传输响应
- `stop`：生成的停止序列
- `n`：要生成的完成数
- `presence_penalty`：基于存在性对新令牌的惩罚
- `frequency_penalty`：基于频率对新令牌的惩罚

带参数的示例：

```python
result = await lm.invoke(
    write_story,
    "魔法森林",
    temperature=0.8,
    max_tokens=200,
    stop=["\n\n"]
)
```
