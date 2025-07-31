---
title: "开发包"
description: "学习如何开发和分发 VAgents 包。"
---

# 开发 VAgents 包

本指南将引导您创建、测试和分发您自己的 VAgents 包。

## 开始

使用包模板生成器创建新包：

```bash
vibe create-template my-awesome-package
```

这将创建一个基本的包结构，您可以根据需要进行自定义。

## 包结构

典型的 VAgents 包包含：

```
my-awesome-package/
├── package.yaml          # 包配置
├── my_awesome_package.py  # 主模块
├── README.md             # 文档
└── requirements.txt      # 可选依赖
```

## 开发工作流

1. **创建包模板**
2. **实现您的功能**
3. **本地测试**
4. **发布到 git 仓库**
5. **通过包管理器安装和测试**

有关详细信息，请参阅[包管理器指南](/zh-cn/guides/package_manager)。
