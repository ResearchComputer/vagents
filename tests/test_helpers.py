"""
Test utilities and fixtures for VAgents testing.

This module provides common utilities, fixtures, and helpers 
to make testing easier and more consistent across the codebase.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import AsyncMock, MagicMock
import pytest

from vagents.core.model import LM
from vagents.core.module import AgentModule, agent_action


class MockLM:
    """Mock LM for testing that simulates fake responses without network calls"""
    
    def __init__(self, name: str = "mock-lm", responses: Optional[List[str]] = None):
        self.name = name
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.calls = []
    
    async def __call__(self, messages: List[Dict], **kwargs):
        """Mock LM call that returns predefined responses"""
        self.call_count += 1
        self.calls.append({"messages": messages, "kwargs": kwargs})
        
        # Cycle through responses
        response_idx = (self.call_count - 1) % len(self.responses)
        response_content = self.responses[response_idx]
        
        return {
            "choices": [
                {
                    "message": {
                        "content": f"[MOCK:{self.name}] {response_content}",
                        "role": "assistant"
                    }
                }
            ]
        }
    
    async def invoke(self, func: Callable, *args, **kwargs):
        """Mock invoke method"""
        messages = func(*args)
        return await self(messages=messages, **kwargs)


class MockAgent(AgentModule):
    """A simple test agent for testing purposes"""
    
    def __init__(self, name: str = "test-agent"):
        super().__init__()
        self.name = name
        self.lm = MockLM(name=f"{name}-lm")
        self.execution_log = []
    
    @agent_action
    async def echo(self, message: str) -> str:
        """Echo action for testing"""
        self.execution_log.append(f"echo: {message}")
        return f"Echo: {message}"
    
    @agent_action
    async def process_with_lm(self, prompt: str) -> Dict[str, Any]:
        """Process prompt with mock LM"""
        self.execution_log.append(f"process_with_lm: {prompt}")
        response = await self.lm(messages=[{"role": "user", "content": prompt}])
        return {
            "prompt": prompt,
            "response": response["choices"][0]["message"]["content"]
        }
    
    async def forward(self, input_data: Any) -> Any:
        """Forward method for testing"""
        self.execution_log.append(f"forward: {input_data}")
        
        if isinstance(input_data, str):
            return f"Processed: {input_data}"
        elif isinstance(input_data, dict):
            action = input_data.get("action")
            if action == "echo":
                return await self.echo(input_data.get("message", ""))
            elif action == "process":
                return await self.process_with_lm(input_data.get("prompt", ""))
        
        return {"processed": input_data, "agent": self.name}


def create_temp_directory() -> Path:
    """Create a temporary directory for testing"""
    return Path(tempfile.mkdtemp())


def create_test_file(directory: Path, filename: str, content: str = "") -> Path:
    """Create a test file with given content"""
    file_path = directory / filename
    file_path.write_text(content)
    return file_path


# Common test fixtures that can be used across test files

@pytest.fixture
def mock_lm():
    """Fixture providing a mock LM"""
    return MockLM()


@pytest.fixture
def test_agent():
    """Fixture providing a test agent"""
    return MockAgent()


@pytest.fixture
def temp_test_dir():
    """Fixture providing a temporary directory that's cleaned up after the test"""
    temp_dir = create_temp_directory()
    yield temp_dir
    # Cleanup
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def fake_lm_env(monkeypatch):
    """Fixture that enables fake LM mode"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")