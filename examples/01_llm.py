from vagents.core import LM


def write_story(query: str) -> str:
    """You will be given a frame of a video, your task is to describe the scene, actions, and any notable details in this video frame."""
    return [{"role": "user", "content": "write a story about " + query}]


if __name__ == "__main__":
    import asyncio

    # Example usage
    async def main():
        lm = LM(
            name="@auto",
        )
        description = await lm.invoke(write_story, "a brave knight and a dragon")
        print(description)

    asyncio.run(main())
