from PIL import Image
from vagents.core import multimodal


@multimodal(input_type="image", param=["frame"])
def narrate_video(frame: Image.Image) -> str:
    """You will be given a frame of a video, your task is to describe the scene, actions, and any notable details in this video frame."""
    return f"Describing frame at index."


if __name__ == "__main__":
    # Example usage
    frame = Image.new(
        "RGB", (100, 100), color="blue"
    )  # Placeholder for an actual video frame
    description = narrate_video(frame=frame)
    print(description)
