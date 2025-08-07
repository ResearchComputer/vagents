---
title: "向量搜索"
description: "高效搜索和检索向量嵌入信息。"
sidebar:
  order: 3
---

# 向量搜索

向量搜索是一种通过比较高维向量表示来寻找语义相似内容的强大技术。本指南将向您展示如何使用 Vagents 的向量搜索功能来构建智能搜索系统。

## 概述

向量搜索的工作原理：
1. 将数据（文本、图像等）转换为数值向量（嵌入）
2. 将这些向量存储在向量数据库中
3. 执行相似性搜索以找到相关内容

## 设置向量搜索

### 1. 导入所需组件

```python
from vagents.core import VecTable, Embedding, Field
from vagents.contrib.impl.libsql_vdb import LibSQLVDB
from vagents.core import multimodal, LM, TextEncoder
from PIL import Image
```

### 2. 初始化向量数据库

```python
# 创建向量数据库实例
vdb = LibSQLVDB(conn_string=".local/sqlite.db")
```

### 3. 定义向量表

创建包含用于存储嵌入的向量字段的表架构：

```python
class GalleryItem(VecTable):
    _table_name = "gallery"
    _vdb = vdb

    name = Field(name="name", field_type=str)
    feature = Field(
        name="feature", field_type=Embedding, dimension=768
    )
    annotation = Field(name="annotation", field_type=str)

    def __init__(self, name: str, feature: list[float], annotation: str = ""):
        super().__init__(name=name, feature=feature, annotation=annotation)
```

## 处理多模态数据

### 创建多模态函数

使用 `@multimodal` 装饰器创建处理不同数据类型的函数：

```python
@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """描述视频帧中的场景、动作和显著细节。"""
    return f"全面描述帧内容，包括动作、物体和场景中存在的任何显著细节。"
```

### 处理图像

```python
def load_remote_image(url: str) -> Image.Image:
    """从远程 URL 加载图像。"""
    import requests
    from io import BytesIO

    response = requests.get(url)
    return Image.open(BytesIO(response.content))
```

## 构建向量搜索系统

### 1. 初始化组件

```python
# 用于将文本转换为向量的文本编码器
encoder = TextEncoder("multi-qa-mpnet-base-cos-v1")

# 用于生成描述的语言模型
model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

# 创建数据库表
vdb.create_all()
```

### 2. 处理和存储数据

```python
photos = [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg",
    # ... 更多照片 URL
]

async def populate_database():
    for photo_url in photos:
        # 加载和处理图像
        frame = load_remote_image(photo_url)

        # 使用多模态 LM 生成描述
        description = await model.invoke(
            narrate_frame,
            frame=frame,
            temperature=0.2,
            max_tokens=256,
            stream=False,
        )
        description = description["choices"][0]["message"]["content"]

        # 将描述转换为向量
        feature = encoder.encode(description)

        # 存储到数据库
        item = GalleryItem(
            name=photo_url,
            feature=feature,
            annotation=description,
        )
        item.insert()
```

### 3. 执行向量搜索

```python
async def search_images():
    # 定义搜索查询
    query_text = "显示一张博物馆中女孩雕像的照片。"

    # 将查询转换为向量
    query_vector = encoder.encode(query_text)

    # 执行向量搜索
    similar_items = GalleryItem.vector_search(
        vector_field="feature",
        query_vector=query_vector,
        top_k=3,
        fields=["name", "annotation"],
    )

    # 处理结果
    print(f"找到 {len(similar_items)} 个相似项目：")
    for i, item in enumerate(similar_items, 1):
        print(f"{i}. URL: {item.name}")
        print(f"   描述: {item.annotation}")
```

## 完整示例

这是一个演示整个向量搜索工作流程的完整示例：

```python
import asyncio
import os
import shutil
from vagents.core import VecTable, Embedding, Field, multimodal, LM, TextEncoder
from vagents.contrib.impl.libsql_vdb import LibSQLVDB
from PIL import Image

# 设置
vdb = LibSQLVDB(conn_string=".local/sqlite.db")
encoder = TextEncoder("multi-qa-mpnet-base-cos-v1")
model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """详细描述场景。"""
    return f"全面描述帧内容，包括动作、物体和场景中存在的任何显著细节。"

def load_remote_image(url: str) -> Image.Image:
    """从远程 URL 加载图像。"""
    import requests
    from io import BytesIO
    response = requests.get(url)
    return Image.open(BytesIO(response.content))

class GalleryItem(VecTable):
    _table_name = "gallery"
    _vdb = vdb

    name = Field(name="name", field_type=str)
    feature = Field(name="feature", field_type=Embedding, dimension=768)
    annotation = Field(name="annotation", field_type=str)

    def __init__(self, name: str, feature: list[float], annotation: str = ""):
        super().__init__(name=name, feature=feature, annotation=annotation)

async def main():
    # 设置数据库
    os.makedirs(".local", exist_ok=True)
    shutil.rmtree(".local/sqlite.db", ignore_errors=True)
    vdb.create_all()

    # 示例数据
    photos = [
        "https://images.unsplash.com/photo-1234567890",
        # ... 更多 URL
    ]

    # 填充数据库
    for photo in photos:
        frame = load_remote_image(photo)
        description = await model.invoke(
            narrate_frame,
            frame=frame,
            temperature=0.2,
            max_tokens=256,
            stream=False,
        )
        description = description["choices"][0]["message"]["content"]
        feature = encoder.encode(description)

        item = GalleryItem(
            name=photo,
            feature=feature,
            annotation=description,
        )
        item.insert()

    # 搜索
    query = "显示一张博物馆中女孩雕像的照片。"
    query_vector = encoder.encode(query)

    results = GalleryItem.vector_search(
        vector_field="feature",
        query_vector=query_vector,
        top_k=3,
        fields=["name", "annotation"],
    )

    for i, item in enumerate(results, 1):
        print(f"{i}. {item.name}: {item.annotation}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 主要特性

- **多模态支持**：处理图像、文本和其他数据类型
- **灵活架构**：定义自定义向量表结构
- **语义搜索**：基于含义而非仅关键词查找内容
- **可扩展存储**：基于 LibSQL 构建，提供高效的向量操作
- **易于集成**：为应用程序添加向量搜索的简单 API

## 最佳实践

1. **选择合适的编码器**：选择与您的领域匹配的文本编码器
2. **优化维度**：在准确性和性能之间取得平衡
3. **批量处理**：高效处理多个项目
4. **查询优化**：尝试不同的查询表述方式
5. **结果过滤**：使用附加字段精炼搜索结果

向量搜索为您的应用程序提供强大的语义发现功能，即使在不存在精确关键词匹配的情况下也能轻松找到相关内容。
