---
title: "包管理器"
description: "学习如何使用 VAgents 包管理器来安装、管理和执行来自 git 仓库的包。"
sidebar:
  order: 4
---

# VAgents 包管理器

VAgents 包管理器（`vibe`）是一个强大的工具，允许您直接从 git 仓库安装、管理和执行代码包。它提供了一种简单的方式来分享和分发可重用的 AI 代理组件、工具和工作流。

## 概述

包管理器使您能够：
- **从任何 git 仓库安装包** 支持子目录和分支选择
- **管理包版本和依赖关系** 具有自动验证功能
- **执行包** 支持动态 CLI 参数解析和管道操作
- **创建和分享包** 使用内置模板
- **搜索和发现可用的包** 通过名称、描述和标签

## 工作原理

整体流程如下：

- 通过读取 `package.yaml|yml|json`（或 `vagents.yaml|yml`）验证包结构，并确保入口文件存在
- 在本地注册表（`~/.vagents/packages/registry.json`）登记包的元信息与安装位置
- 在隔离的执行上下文中从包目录加载并执行配置的 `entry_point`，期间临时修改 `sys.path`
- 支持两类执行模式：
  - 协议感知（Agent-aware）：若入口为 `AgentModule` 子类，或函数接受 `AgentInput`，管理器会从 CLI 参数/标准输入构造 `AgentInput`，并在可能时将返回值封装为 `AgentOutput`
  - 传统可调用（Legacy）：若入口为普通函数/类，则按解析得到的参数调用；若检测到标准输入，则尝试以 `input`/`stdin`/`content` 名称传入

这使得基于 `AgentModule` 的实现可以无缝运行，同时兼容更简单的可调用入口。

## 安装

包管理器与 VAgents 捆绑在一起。一旦您安装了 VAgents，您就可以使用 `vibe` 命令：

```bash
pip install v-agents
```

验证安装：

```bash
vibe --help
```

## 基本用法

### 安装包

从 git 仓库安装包：

```bash
vibe install https://github.com/username/my-package.git
```

从仓库内的子目录安装：

```bash
vibe install https://github.com/username/my-package.git/subdir
```

### 列出已安装的包

查看所有已安装的包：

```bash
vibe list
```

以 JSON 格式获取输出：

```bash
vibe list --format json
```

### 包信息

获取特定包的详细信息：

```bash
vibe info my-package
```

### 更新包

将包更新到最新版本：

```bash
vibe update my-package
```

### 卸载包

移除包：

```bash
vibe uninstall my-package
```

### 执行包

运行包：

```bash
vibe run my-package
```

向包传递参数：

```bash
vibe run my-package --args "arg1" "arg2" "arg3"
```

以 JSON 格式传递关键字参数：

```bash
vibe run my-package --kwargs '{"param1": "value1", "param2": 42}'
```

选择输出格式：

```bash
vibe run my-package --format rich    # 富格式输出（默认）
vibe run my-package --format plain   # 纯文本输出
vibe run my-package --format json    # JSON 输出
vibe run my-package --format markdown # Markdown 输出
```

### 包管理器状态

检查包管理器状态：

```bash
vibe status
```

这将显示：
- 基础目录位置
- 已安装包的数量
- 包摘要和版本
- 总磁盘使用量

## 创建包

### 包模板

创建新的包模板：

```bash
vibe create-template my-new-package
```

在特定目录中创建：

```bash
vibe create-template my-new-package --output-dir ./packages
```

这将创建包含以下内容的包结构：
- `package.yaml` - 包配置
- `my-new-package.py` - 主模块
- `README.md` - 文档

### 包配置

每个包都需要一个 `package.yaml` 配置文件：

```yaml
name: my-package
version: 1.0.0
description: 一个示例 VAgents 包
author: 您的姓名
repository_url: https://github.com/yourusername/my-package.git
entry_point: my_package.main
dependencies: []
python_version: ">=3.8"
tags:
  - vagents
  - example
```

**配置字段：**

- `name`: 包标识符（必需）
- `version`: 语义版本字符串（必需）
- `description`: 简短的包描述（必需）
- `author`: 包作者姓名（必需）
- `repository_url`: Git 仓库 URL（必需）
- `entry_point`: 要执行的 Module.function 或 Module.Class（必需）
- `dependencies`: Python 包依赖列表
- `python_version`: 最低 Python 版本要求
- `tags`: 用于分类和搜索的标签列表

### 包入口点

入口点必须是可以接受参数的可调用函数或类：

```python
def main(*args, **kwargs):
    """
    包的主入口点

    Args:
        *args: 来自命令行的位置参数
        **kwargs: 来自命令行的关键字参数

    Returns:
        Any: 将显示给用户的结果
    """
    return {
        "message": "来自我的包的问候！",
        "args": args,
        "kwargs": kwargs
    }
```

或具有可调用接口的类：

```python
class MyPackage:
    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

    def execute(self, *args, **kwargs):
        # 在这里实现
        return {"result": "success"}
```

### 发布包

1. 使用模板创建您的包
2. 在主模块中实现您的功能
3. 更新 `package.yaml` 中的配置
4. 初始化 git 仓库：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```
5. 推送到远程仓库（GitHub、GitLab 等）
6. 用户可以使用以下命令安装：
   ```bash
   vibe install https://github.com/yourusername/my-package.git
   ```

## 高级用法

### 调试模式

通过设置环境变量启用调试日志记录：

```bash
export LOGLEVEL=DEBUG
vibe install https://github.com/username/package.git
```

### 安全考虑

1. **信任您的来源** - 仅从可信仓库安装包
2. **查看包代码** - 安装前检查源代码
3. **使用版本固定** - 在生产环境中固定到特定版本
4. **定期更新** - 保持包更新以获得安全补丁
