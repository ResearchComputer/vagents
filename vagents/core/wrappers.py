from typing import Optional, List, Callable, Any
from vagents.utils import image_to_base64


def multimodal(
    orig_func: Optional[Callable[..., Any]] = None,
    input_type: Optional[str] = None,
    param: Optional[List[str]] = None,
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            image_contents = []
            if input_type and param:
                for p in param:
                    if p in kwargs:
                        if input_type == "image":
                            image_contents.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_to_base64(kwargs[p])}"
                                    },
                                }
                            )
            prompt = func(*args, **kwargs)
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        *image_contents,
                    ],
                }
            ]

        return wrapper

    return decorator
