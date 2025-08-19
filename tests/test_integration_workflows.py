import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from vagents.core.model import LM
from vagents.core.module import AgentModule, agent_action
from vagents.core.executor import get_executor


class TestWorkflowAgent(AgentModule):
    """Test agent for integration testing"""
    
    def __init__(self, lm_name: str = "test-model"):
        super().__init__()
        self.lm = LM(name=lm_name)
        self.process_count = 0
    
    @agent_action
    async def analyze_text(self, text: str) -> dict:
        """Analyze text using LM"""
        messages = [{"role": "user", "content": f"Analyze: {text}"}]
        response = await self.lm(messages=messages)
        self.process_count += 1
        return {
            "analysis": response["choices"][0]["message"]["content"],
            "word_count": len(text.split()),
            "char_count": len(text)
        }
    
    @agent_action
    async def summarize_batch(self, texts: list) -> list:
        """Process multiple texts concurrently"""
        tasks = []
        for text in texts:
            messages = [{"role": "user", "content": f"Summarize: {text}"}]
            tasks.append(self.lm(messages=messages))
        
        responses = await asyncio.gather(*tasks)
        self.process_count += len(texts)
        
        return [
            {
                "text": text,
                "summary": resp["choices"][0]["message"]["content"]
            }
            for text, resp in zip(texts, responses)
        ]
    
    async def forward(self, input_data: dict) -> dict:
        """Main processing workflow"""
        if "action" not in input_data:
            return {"error": "No action specified"}
        
        action = input_data["action"]
        
        if action == "analyze":
            text = input_data.get("text", "")
            return await self.analyze_text(text)
        elif action == "batch_summarize":
            texts = input_data.get("texts", [])
            return {"summaries": await self.summarize_batch(texts)}
        else:
            return {"error": f"Unknown action: {action}"}


@pytest.mark.asyncio
async def test_agent_lm_integration_workflow(monkeypatch):
    """Test complete workflow with agent and LM integration"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    agent = TestWorkflowAgent()
    
    # Test single text analysis
    input_data = {
        "action": "analyze",
        "text": "This is a test document for analysis."
    }
    
    result = await agent(input_data)
    
    assert "analysis" in result
    assert "word_count" in result
    assert "char_count" in result
    assert result["word_count"] == 7
    assert result["char_count"] == 38
    assert "[FAKE:test-model]" in result["analysis"]
    assert agent.process_count == 1


@pytest.mark.asyncio
async def test_agent_batch_processing_workflow(monkeypatch):
    """Test batch processing workflow"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    agent = TestWorkflowAgent()
    
    # Test batch summarization
    input_data = {
        "action": "batch_summarize",
        "texts": [
            "First document to summarize",
            "Second document for processing",
            "Third text for batch analysis"
        ]
    }
    
    result = await agent(input_data)
    
    assert "summaries" in result
    assert len(result["summaries"]) == 3
    
    for i, summary in enumerate(result["summaries"]):
        assert "text" in summary
        assert "summary" in summary
        assert summary["text"] == input_data["texts"][i]
        assert "[FAKE:test-model]" in summary["summary"]
    
    assert agent.process_count == 3


@pytest.mark.asyncio
async def test_concurrent_agent_instances():
    """Test multiple agent instances working concurrently"""
    
    async def agent_workflow(agent_id: str, texts: list):
        agent = TestWorkflowAgent(lm_name=f"model-{agent_id}")
        
        results = []
        for text in texts:
            result = await agent.analyze_text(text)
            results.append(result)
        
        return agent_id, results
    
    # Run multiple agents concurrently
    agents_data = [
        ("agent1", ["Text for agent 1", "Another text for agent 1"]),
        ("agent2", ["Text for agent 2", "Second text for agent 2"]),
        ("agent3", ["Text for agent 3"])
    ]
    
    with patch.dict('os.environ', {'VAGENTS_LM_FAKE': '1'}):
        tasks = [agent_workflow(agent_id, texts) for agent_id, texts in agents_data]
        results = await asyncio.gather(*tasks)
    
    # Verify all agents completed successfully
    assert len(results) == 3
    
    for agent_id, agent_results in results:
        assert agent_id.startswith("agent")
        assert len(agent_results) > 0
        
        for result in agent_results:
            assert "analysis" in result
            assert "word_count" in result
            assert "char_count" in result


@pytest.mark.asyncio
async def test_agent_error_handling_workflow(monkeypatch):
    """Test agent handles errors gracefully in workflows"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    agent = TestWorkflowAgent()
    
    # Test invalid action
    invalid_input = {"action": "invalid_action"}
    result = await agent(invalid_input)
    assert "error" in result
    assert "Unknown action" in result["error"]
    
    # Test missing action
    missing_action_input = {"text": "some text"}
    result = await agent(missing_action_input)
    assert "error" in result
    assert "No action specified" in result["error"]


@pytest.mark.asyncio
async def test_executor_agent_integration():
    """Test executor integration with agent workflows"""
    
    class ExecutorTestAgent(AgentModule):
        async def forward(self, delay: float):
            await asyncio.sleep(delay)
            return f"completed after {delay}s"
    
    executor = get_executor()
    agent = ExecutorTestAgent()
    
    # Test agent execution through executor
    start_time = asyncio.get_event_loop().time()
    
    # Start multiple tasks with different delays
    future1 = agent(0.01)
    future2 = agent(0.02)
    future3 = agent(0.01)
    
    results = await asyncio.gather(future1, future2, future3)
    
    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time
    
    # Should complete in roughly the time of the longest task (0.02s)
    # plus some overhead, but much less than sum of all delays (0.04s)
    assert total_time < 0.1  # Much less than sequential execution
    
    assert len(results) == 3
    for result in results:
        assert "completed after" in result


@pytest.mark.asyncio
async def test_agent_action_chaining():
    """Test chaining agent actions together"""
    
    class ChainAgent(AgentModule):
        @agent_action
        async def step_one(self, x: int) -> int:
            return x * 2
        
        @agent_action
        async def step_two(self, x: int) -> int:
            return x + 10
        
        @agent_action
        async def step_three(self, x: int) -> str:
            return f"result: {x}"
        
        async def forward(self, x: int) -> str:
            # Chain actions together
            result1 = await self.step_one(x)
            result2 = await self.step_two(result1)
            result3 = await self.step_three(result2)
            return result3
    
    agent = ChainAgent()
    
    # Test action chaining
    final_result = await agent(5)
    # 5 * 2 = 10, 10 + 10 = 20, "result: 20"
    assert final_result == "result: 20"
    
    # Test individual actions work
    assert await agent.actions["step_one"](5) == 10
    assert await agent.actions["step_two"](10) == 20
    assert await agent.actions["step_three"](20) == "result: 20"


@pytest.mark.asyncio
async def test_agent_with_lm_parameter_filtering(monkeypatch):
    """Test that LM parameter filtering works correctly in agent context"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    class ParameterAgent(AgentModule):
        def __init__(self):
            super().__init__()
            self.lm = LM(name="param-test")
        
        async def forward(self, prompt: str, **kwargs):
            def make_messages(text):
                return [{"role": "user", "content": text}]
            
            # This should filter out invalid LM parameters
            response = await self.lm.invoke(
                make_messages, 
                prompt,
                temperature=0.7,  # Valid LM param
                max_tokens=100,   # Valid LM param
                custom_param="should_be_filtered",  # Invalid LM param
                another_param=42  # Invalid LM param
            )
            return response
    
    agent = ParameterAgent()
    
    result = await agent("test prompt")
    assert "choices" in result
    assert "[FAKE:param-test]" in result["choices"][0]["message"]["content"]
    assert "test prompt" in result["choices"][0]["message"]["content"]