---
title: "开发包"
description: "学习如何开发和分发具有 CLI 参数、管道支持和正确结构的 VAgents 包。"
sidebar:
  order: 2
---

# 开发 VAgents 包

本综合指南将引导您创建、测试和分发自己的 VAgents 包，包括 CLI 参数解析、管道支持和适当的错误处理等高级功能。

## 开始

使用包模板生成器创建新包：

```bash
vibe create-template my-awesome-package
```

在特定目录中创建：

```bash
vibe create-template my-awesome-package --output-dir ./packages
```

这创建了一个完整的包结构，您可以根据需要进行自定义。

## 包结构

典型的 VAgents 包包含：

```
my-awesome-package/
├── package.yaml              # 包配置与 CLI 参数
├── my_awesome_package.py     # 主模块与示例实现
├── README.md                 # 完整文档
└── requirements.txt          # 可选的 Python 依赖
```

### 生成的文件

当您创建模板时，您会得到：

1. **package.yaml** - 预配置常用 CLI 参数
2. **主模块** - 带有管道支持的示例实现
3. **README.md** - 使用示例和文档
4. **Git 就绪结构** - 准备版本控制

## 包配置深入了解

### 基本配置

```yaml
name: my-awesome-package
version: 1.0.0
description: 处理数据的绝佳包
author: 您的姓名
repository_url: https://github.com/yourusername/my-awesome-package.git
entry_point: my_awesome_package.main
dependencies:
  - requests
  - numpy
python_version: ">=3.8"
tags:
  - data-processing
  - analysis
  - awesome
```

### CLI 参数配置

定义自动解析的高级 CLI 参数：

```yaml
arguments:
  # 布尔标志
  - name: verbose
    type: bool
    help: 启用详细输出
    short: v
    required: false

  # 带选择的字符串
  - name: format
    type: str
    help: 输出格式
    short: f
    choices: [json, xml, csv]
    default: json
    required: false

  # 带验证的整数
  - name: history
    type: int
    help: 要处理的记录数
    default: 10
    required: false

  # 必需字符串
  - name: config
    type: str
    help: 配置文件路径
    short: c
    required: true

  # 值列表
  - name: tags
    type: list
    help: 过滤的标签
    short: t
    required: false
```

## 实现模式

### AgentModule + 协议（推荐）

使用 `AgentModule` 搭配 `AgentInput`/`AgentOutput` 协议可以让包管理器进行“协议感知（Agent-aware）”的执行：它会自动把 CLI 参数与管道输入组装为 `AgentInput`，并在可行时把返回的字典封装为 `AgentOutput`。

类入口示例：

```python
# my_agent_package.py
from vagents.core import AgentModule, AgentInput, AgentOutput

class MyAgent(AgentModule):
    async def forward(self, input: AgentInput) -> AgentOutput:
        # 你的逻辑
        return AgentOutput(input_id=input.id, result={"echo": input.payload})
```

函数入口示例：

```python
# my_agent_package.py
from vagents.core import AgentInput, AgentOutput

async def run(input: AgentInput) -> AgentOutput:
    return AgentOutput(input_id=input.id, result={"echo": input.payload})
```

在 `package.yaml` 中配置入口：

```yaml
entry_point: my_agent_package.MyAgent   # 或 my_agent_package.run
```

### 基本实现

```python
def main(verbose=False, config=None, input=None, stdin=None, **kwargs):
    """
    my-awesome-package 包的主入口点

    Args:
        verbose (bool): 启用详细输出
        config (str): 配置文件路径
        input (str): 输入内容（使用管道时来自 stdin）
        stdin (str): 标准输入内容（input 参数的别名）
        **kwargs: 来自 CLI 的额外关键字参数

    Returns:
        dict: 包执行的结果
    """
    # 处理 stdin 输入（input 和 stdin 是别名）
    content = input or stdin

    result = {
        "message": "来自 my-awesome-package 的问候！",
        "verbose": verbose,
        "config": config,
        "has_input": content is not None,
        "additional_args": kwargs
    }

    if verbose:
        print(f"详细模式已启用")
        print(f"配置文件：{config}")
        if content:
            print(f"正在处理 {len(content)} 个字符的输入")

    # 如果提供了输入内容则进行处理
    if content:
        result["processed_input"] = process_content(content)

    return result
```

### 高级实现与错误处理

```python
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

def main(
    verbose: bool = False,
    config: Optional[str] = None,
    format: str = "json",
    history: int = 10,
    tags: Optional[list] = None,
    input: Optional[str] = None,
    stdin: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    具有完整错误处理的高级包实现
    """
    try:
        # 使用类型安全默认值初始化
        content = input or stdin
        tags = tags or []

        # 如果提供则加载配置
        config_data = {}
        if config:
            config_data = load_config(config)

        # 验证输入
        if history < 1:
            raise ValueError("历史记录必须是正整数")

        if format not in ["json", "xml", "csv"]:
            raise ValueError(f"不支持的格式：{format}")

        # 处理请求
        result = {
            "status": "success",
            "format": format,
            "history_count": history,
            "tags": tags,
            "config_loaded": bool(config_data),
            "has_input": content is not None,
            "timestamp": get_timestamp()
        }

        # 处理输入内容
        if content:
            try:
                processed = process_content(content, format, history, tags)
                result["processed_data"] = processed

                if verbose:
                    print(f"成功处理了 {len(content)} 个字符")
                    print(f"生成了 {len(processed)} 条记录")

            except Exception as e:
                if verbose:
                    print(f"处理内容时出错：{e}")
                result["processing_error"] = str(e)

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
```

## 开发工作流

### 1. 创建和初始化

```bash
# 创建包模板
vibe create-template my-data-processor --output-dir ./packages

# 导航到包目录
cd packages/my-data-processor

# 初始化 git 仓库
git init
git add .
git commit -m "Initial package structure"
```

### 2. 实现和测试

```bash
# 直接测试您的实现
python my_data_processor.py --verbose --config test.json

# 使用管道输入测试
echo "测试数据" | python my_data_processor.py --verbose

# 使用文件输入测试
cat sample_data.txt | python my_data_processor.py --format json --history 5
```

### 3. 本地测试

```bash
# 本地安装进行测试
vibe install /absolute/path/to/packages/my-data-processor

# 通过包管理器测试
vibe run my-data-processor --verbose --config test.json

# 使用管道测试
cat data.txt | vibe run my-data-processor --format csv --history 10
```

### 4. 打包和发布

```bash
# 使用最终详细信息更新 package.yaml
# 推送到远程仓库
git remote add origin https://github.com/yourusername/my-data-processor.git
git push -u origin main

# 标记发布
git tag v1.0.0
git push --tags
```

## 最佳实践

### 1. 错误处理
- 始终验证输入参数
- 提供有意义的错误消息
- 在结果中返回错误信息
- 优雅地处理缺失文件

### 2. 文档
- 使用清晰描述性的帮助文本
- 在 README 中包含使用示例
- 记录所有 CLI 参数
- 提供故障排除提示

### 3. 输入处理
- 支持直接和管道输入
- 处理不同的数据格式
- 在处理前验证输入
- 支持大文件处理

### 4. 输出格式化
- 返回结构化数据（dict/list）
- 支持不同的输出格式
- 在结果中包含元数据
- 使输出机器可读

### 5. 配置
- 支持配置文件
- 提供合理的默认值
- 允许运行时覆盖
- 验证配置

有关使用包的详细信息，请参阅[包管理器指南](/zh-cn/guides/package_manager)。
