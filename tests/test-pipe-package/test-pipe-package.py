"""
test-pipe-package - A VAgents Package

This is the main module for the test-pipe-package package.
"""


def main(verbose=False, config=None, input=None, stdin=None, **kwargs):
    """
    Main entry point for the test-pipe-package package

    Args:
        verbose (bool): Enable verbose output
        config (str): Configuration file path
        input (str): Input content (from stdin when using pipes)
        stdin (str): Standard input content (alias for input)
        **kwargs: Additional keyword arguments

    Returns:
        dict: Result of the package execution
    """
    # Handle stdin input (input and stdin are aliases)
    content = input or stdin

    result = {
        "message": f"Hello from test-pipe-package package!",
        "verbose": verbose,
        "config": config,
        "has_input": content is not None,
        "input_length": len(content) if content else 0,
        "additional_args": kwargs,
    }

    if verbose:
        print(f"Verbose mode enabled for test-pipe-package")
        if config:
            print(f"Using config file: {config}")
        if content:
            print(f"Processing {len(content)} characters of input")
            print(f"Input preview: {repr(content[:100])}")

    # Process the input content if provided
    if content:
        result["processed_input"] = {
            "length": len(content),
            "lines": len(content.splitlines()) if content else 0,
            "words": len(content.split()) if content else 0,
            "first_line": content.splitlines()[0]
            if content and content.splitlines()
            else None,
        }

        # Example processing based on content
        if "error" in content.lower():
            result["analysis"] = "Input contains error messages"
        elif "success" in content.lower():
            result["analysis"] = "Input contains success messages"
        else:
            result["analysis"] = "Input analyzed successfully"

    return result


if __name__ == "__main__":
    # Example: python test-pipe-package.py --verbose --config myconfig.json
    # Example with pipe: echo "test data" | python test-pipe-package.py --verbose
    import sys

    # Check for stdin input when run directly
    stdin_content = None
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip()

    result = main(verbose=True, input=stdin_content)
    print(result)
