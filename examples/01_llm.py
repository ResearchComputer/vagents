from vagents.core import LM


def write_story(query: str, *args, **kwargs) -> str:
    """You are a helpful assistant."""
    return [{"role": "user", "content": "write a story about " + query}]


if __name__ == "__main__":
    import asyncio

    # Example usage
    async def main():
        lm = LM(
            name="@auto",
        )
        description = await lm.invoke(write_story, "a brave knight and a dragon")
        description = description["choices"][0]["message"]["content"]
        print(description)

    asyncio.run(main())
