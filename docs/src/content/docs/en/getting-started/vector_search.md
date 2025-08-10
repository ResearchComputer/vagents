---
title: "Vector Search"
description: "Efficiently searching and retrieving information from vector embeddings."
sidebar:
  order: 3
---

# Vector Search

Vector search is a powerful technique for finding semantically similar content by comparing high-dimensional vector representations. This guide shows you how to use Vagents' vector search capabilities to build intelligent search systems.

## Overview

Vector search works by:
1. Converting data (text, images, etc.) into numerical vectors (embeddings)
2. Storing these vectors in a vector database
3. Performing similarity searches to find related content

## Setting up Vector Search

### 1. Import Required Components

```python
from vagents.core import VecTable, Embedding, Field
from vagents.contrib.impl.libsql_vdb import LibSQLVDB
from vagents.core import multimodal, LM, TextEncoder
from PIL import Image
```

### 2. Initialize Vector Database

```python
# Create a vector database instance
vdb = LibSQLVDB(conn_string=".local/sqlite.db")
```

### 3. Define a Vector Table

Create a table schema that includes vector fields for storing embeddings:

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

## Working with Multimodal Data

### Creating Multimodal Functions

Use the `@multimodal` decorator to create functions that process different data types:

```python
@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """Describe the scene, actions, and notable details in a video frame."""
    return f"Describe the frame comprehensively, including the actions, objects, and any notable details present in the scene."
```

### Processing Images

```python
def load_remote_image(url: str) -> Image.Image:
    """Load an image from a remote URL."""
    import requests
    from io import BytesIO

    response = requests.get(url)
    return Image.open(BytesIO(response.content))
```

## Building a Vector Search System

### 1. Initialize Components

```python
# Text encoder for converting text to vectors
encoder = TextEncoder("multi-qa-mpnet-base-cos-v1")

# Language model for generating descriptions
model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

# Create database tables
vdb.create_all()
```

### 2. Process and Store Data

```python
photos = [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg",
    # ... more photo URLs
]

async def populate_database():
    for photo_url in photos:
        # Load and process the image
        frame = load_remote_image(photo_url)

        # Generate description using multimodal LM
        description = await model.invoke(
            narrate_frame,
            frame=frame,
            temperature=0.2,
            max_tokens=256,
            stream=False,
        )
        description = description["choices"][0]["message"]["content"]

        # Convert description to vector
        feature = encoder.encode(description)

        # Store in database
        item = GalleryItem(
            name=photo_url,
            feature=feature,
            annotation=description,
        )
        item.insert()
```

### 3. Perform Vector Search

```python
async def search_images():
    # Define your search query
    query_text = "Show me a photo of a statue of a girl in the museum."

    # Convert query to vector
    query_vector = encoder.encode(query_text)

    # Perform vector search
    similar_items = GalleryItem.vector_search(
        vector_field="feature",
        query_vector=query_vector,
        top_k=3,
        fields=["name", "annotation"],
    )

    # Process results
    print(f"Found {len(similar_items)} similar items:")
    for i, item in enumerate(similar_items, 1):
        print(f"{i}. URL: {item.name}")
        print(f"   Description: {item.annotation}")
```

## Complete Example

Here's a complete working example that demonstrates the entire vector search workflow:

```python
import asyncio
import os
import shutil
from vagents.core import VecTable, Embedding, Field, multimodal, LM, TextEncoder
from vagents.contrib.impl.libsql_vdb import LibSQLVDB
from PIL import Image

# Setup
vdb = LibSQLVDB(conn_string=".local/sqlite.db")
encoder = TextEncoder("multi-qa-mpnet-base-cos-v1")
model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """Describe the scene in detail."""
    return f"Describe the frame comprehensively, including the actions, objects, and any notable details present in the scene."

def load_remote_image(url: str) -> Image.Image:
    """Load an image from a remote URL."""
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
    # Setup database
    os.makedirs(".local", exist_ok=True)
    shutil.rmtree(".local/sqlite.db", ignore_errors=True)
    vdb.create_all()

    # Sample data
    photos = [
        "https://images.unsplash.com/photo-1234567890",
        # ... more URLs
    ]

    # Populate database
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

    # Search
    query = "Show me a photo of a statue of a girl in the museum."
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

## Key Features

- **Multimodal Support**: Process images, text, and other data types
- **Flexible Schema**: Define custom vector table structures
- **Semantic Search**: Find content based on meaning, not just keywords
- **Scalable Storage**: Built on LibSQL for efficient vector operations
- **Easy Integration**: Simple API for adding vector search to applications

## Best Practices

1. **Choose appropriate encoders**: Select text encoders that match your domain
2. **Optimize dimensions**: Balance between accuracy and performance
3. **Batch processing**: Process multiple items efficiently
4. **Query optimization**: Experiment with different query formulations
5. **Result filtering**: Use additional fields to refine search results

Vector search enables powerful semantic discovery capabilities in your applications, making it easy to find relevant content even when exact keyword matches don't exist.
