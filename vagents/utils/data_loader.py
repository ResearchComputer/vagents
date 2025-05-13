import json
from typing import Optional, Callable


def read_jsonl(
    file_path,
    skip_invalid=True,
    order_by: Optional[str] = None,
    keep_only: Optional[Callable] = None,
):
    """Read JSONL file and return list of JSON objects."""
    data = []
    with open(file_path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                if skip_invalid:
                    continue
                else:
                    raise ValueError(f"Invalid JSON: {line}")
    if keep_only:
        data = [item for item in data if keep_only(item)]
    print(f"Loaded {len(data)} items from {file_path}")
    if order_by:
        """order_by is a key in the JSON object, could also be comma-separated path to the key"""

        def get_nested_value(item, path):
            """Get value from nested dictionary using dot notation path."""
            keys = path.split(".")
            value = item
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value

        # Use a custom sorting key that handles None values
        # The (value is not None, value) tuple puts None values last and sorts non-None values normally
        data = sorted(
            data,
            key=lambda x: (
                get_nested_value(x, order_by) is not None,
                get_nested_value(x, order_by),
            ),
        )
    # add a index to the data
    data = [{"index": i, **item} for i, item in enumerate(data)]
    return data
