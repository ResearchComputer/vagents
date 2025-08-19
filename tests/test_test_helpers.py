"""Test the test helpers to ensure they work correctly"""

import pytest
import asyncio
from tests.test_helpers import MockLM, MockAgent


@pytest.mark.asyncio
async def test_mock_lm_basic_functionality():
    """Test that MockLM works as expected"""
    mock_lm = MockLM(name="test-mock", responses=["Response 1", "Response 2"])
    
    # Test first call
    result1 = await mock_lm(messages=[{"role": "user", "content": "Hello"}])
    assert result1["choices"][0]["message"]["content"] == "[MOCK:test-mock] Response 1"
    
    # Test second call (should cycle to second response)
    result2 = await mock_lm(messages=[{"role": "user", "content": "Hi"}])
    assert result2["choices"][0]["message"]["content"] == "[MOCK:test-mock] Response 2"
    
    # Test third call (should cycle back to first response)
    result3 = await mock_lm(messages=[{"role": "user", "content": "Hey"}])
    assert result3["choices"][0]["message"]["content"] == "[MOCK:test-mock] Response 1"
    
    # Check call tracking
    assert mock_lm.call_count == 3
    assert len(mock_lm.calls) == 3
    assert mock_lm.calls[0]["messages"][0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_mock_agent_functionality():
    """Test that MockAgent works as expected"""
    agent = MockAgent(name="test-agent")
    
    # Test echo action
    echo_result = await agent.actions["echo"]("Hello World")
    assert echo_result == "Echo: Hello World"
    assert "echo: Hello World" in agent.execution_log
    
    # Test process_with_lm action
    process_result = await agent.actions["process_with_lm"]("Test prompt")
    assert process_result["prompt"] == "Test prompt"
    assert "[MOCK:test-agent-lm]" in process_result["response"]
    assert "process_with_lm: Test prompt" in agent.execution_log
    
    # Test forward method with string
    forward_result = await agent("test input")
    assert forward_result == "Processed: test input"
    assert "forward: test input" in agent.execution_log
    
    # Test forward method with dict (echo action)
    dict_input = {"action": "echo", "message": "test message"}
    dict_result = await agent(dict_input)
    assert dict_result == "Echo: test message"
    
    # Test forward method with dict (process action)
    process_input = {"action": "process", "prompt": "test prompt"}
    process_result = await agent(process_input)
    assert process_result["prompt"] == "test prompt"
    assert "[MOCK:test-agent-lm]" in process_result["response"]


def test_test_helpers_import():
    """Test that test helpers can be imported correctly"""
    from tests.test_helpers import MockLM, MockAgent, create_temp_directory, create_test_file
    
    # Basic functionality test
    temp_dir = create_temp_directory()
    assert temp_dir.exists()
    
    test_file = create_test_file(temp_dir, "test.txt", "test content")
    assert test_file.exists()
    assert test_file.read_text() == "test content"
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_mock_lm_invoke_method():
    """Test MockLM invoke method"""
    mock_lm = MockLM(responses=["Invoke response"])
    
    def make_messages(prompt):
        return [{"role": "user", "content": prompt}]
    
    result = await mock_lm.invoke(make_messages, "test prompt")
    assert result["choices"][0]["message"]["content"] == "[MOCK:mock-lm] Invoke response"
    
    # Check that invoke was tracked correctly
    assert mock_lm.call_count == 1
    assert mock_lm.calls[0]["messages"][0]["content"] == "test prompt"


def test_fixtures_available():
    """Test that fixtures are available for import"""
    from tests.test_helpers import mock_lm, test_agent, temp_test_dir, fake_lm_env
    
    # Just check they're callable (they're pytest fixtures)
    assert callable(mock_lm)
    assert callable(test_agent)
    assert callable(temp_test_dir)
    assert callable(fake_lm_env)