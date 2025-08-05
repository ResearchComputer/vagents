from PIL import Image
from vagents.core import multimodal, LM


@multimodal(input_type="image", param=["frame"])
def narrate_frame(frame: Image.Image, *args, **kwargs) -> str:
    """You will be given a frame of a video, your task is to describe the scene, actions, and any notable details in this video frame. You are a helpful assistant."""
    return f"Describing frame at index."


def load_remote_image(url: str) -> Image.Image:
    """Load an image from a remote URL."""
    import requests
    from io import BytesIO

    response = requests.get(url)
    return Image.open(BytesIO(response.content))


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        frame = load_remote_image(
            "https://images.unsplash.com/photo-1751156070009-aa14ed1a2661?ixlib=rb-4.1.0&q=85&fm=jpg&crop=entropy&cs=srgb&dl=xiaozhe-yao-mBVNlXtFgz0-unsplash.jpg&w=640"
        )
        model = LM(name="meta-llama/Llama-3.2-90B-Vision-Instruct")
        description = await model.invoke(
            narrate_frame, frame=frame, temperature=0.7, max_tokens=100, stream=False
        )
        print(description)

    asyncio.run(main())
