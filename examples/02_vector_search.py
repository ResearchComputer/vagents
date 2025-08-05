from vagents.core import VecTable, Embedding, Field
from vagents.contrib.impl.libsql_vdb import LibSQLVDB
from PIL import Image
from vagents.core import multimodal, LM, TextEncoder


@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """You will be given a frame of a video, your task is to describe the scene, actions, and any notable details in this video frame. You are a helpful assistant."""
    return f"Describe the frame comprehensively, including the actions, objects, and any notable details present in the scene."


def load_remote_image(url: str) -> Image.Image:
    """Load an image from a remote URL."""
    import requests
    from io import BytesIO

    response = requests.get(url)
    return Image.open(BytesIO(response.content))


vdb = LibSQLVDB(conn_string=".local/sqlite.db")
photos = [
    "https://images.unsplash.com/photo-1751156070009-aa14ed1a2661?ixlib=rb-4.1.0&q=85&fm=jpg&crop=entropy&cs=srgb&dl=xiaozhe-yao-mBVNlXtFgz0-unsplash.jpg&w=640",
    "https://images.unsplash.com/photo-1691094168684-85ac993a48f3?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
    "https://images.unsplash.com/photo-1723587590292-5b576a12b38b?q=80&w=987&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
    "https://images.unsplash.com/photo-1691094932768-e97f2507b866?q=80&w=1974&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
]


class GalleryItem(VecTable):
    _table_name = "gallery"
    _vdb = vdb

    name = Field(name="name", field_type=str)
    feature = Field(
        name="feature", field_type=Embedding, dimension=768
    )  # Updated to typical embedding dimension
    annotation = Field(name="annotation", field_type=str)

    def __init__(self, name: str, feature: list[float], annotation: str = ""):
        super().__init__(name=name, feature=feature, annotation=annotation)


if __name__ == "__main__":
    import asyncio
    import shutil
    import os

    encoder = TextEncoder("multi-qa-mpnet-base-cos-v1")
    model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")

    # Create the directory if it doesn't exist
    os.makedirs(".local", exist_ok=True)
    shutil.rmtree(".local/sqlite.db", ignore_errors=True)

    async def main():
        vdb.create_all()
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

        # Now perform vector search
        query_item = "Show me a photo of a statue of a girl in the museum."
        print(f"Searching for: {query_item}")

        # Encode the query text into a vector
        query_vector = encoder.encode(query_item)

        # Perform vector search to find similar images
        similar_items = GalleryItem.vector_search(
            vector_field="feature",
            query_vector=query_vector,
            top_k=3,
            fields=["name", "annotation"],
        )
        print(f"\nFound {len(similar_items)} similar items:")
        for i, item in enumerate(similar_items, 1):
            print(f"{i}. URL: {item.name}")
            print(f"   Description: {item.annotation}")
            print()

    asyncio.run(main())
