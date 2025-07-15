"""
Test configuration and fixtures for the vagents test suite.
"""
import pytest
import asyncio
from typing import Dict, Any


@pytest.fixture
def sample_context():
    """Provide a sample execution context for testing."""
    return {
        "x": 1,
        "y": 2,
        "result": None,
        "__builtins__": __builtins__,
    }


@pytest.fixture
def async_context():
    """Provide an async execution context for testing."""

    async def mock_async_func(value):
        await asyncio.sleep(0.01)  # Simulate async work
        return value * 2

    return {
        "mock_async_func": mock_async_func,
        "x": 5,
        "y": 10,
        "__builtins__": __builtins__,
    }


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class MockLLM:
    """Mock LLM for testing purposes."""

    def __init__(self, responses=None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


@pytest.fixture
def mock_llm():
    """Provide a mock LLM for testing."""
    return MockLLM()


@pytest.fixture
def sample_graph_data():
    """Provide sample data for graph construction tests."""
    return {
        "simple_assignment": "x = 5",
        "await_assignment": "result = await some_async_func()",
        "condition": "if x > 0:",
        "return_stmt": "return result",
        "break_stmt": "break",
    }
