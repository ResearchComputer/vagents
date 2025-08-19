import asyncio
import pytest

from vagents.core.module import AgentModule, agent_action


class ToyAgent(AgentModule):
    @agent_action
    async def greet(self, name: str) -> str:
        await asyncio.sleep(0)
        return f"hello {name}"

    async def forward(self, x: int) -> int:
        await asyncio.sleep(0)
        return x + 1


@pytest.mark.asyncio
async def test_agentmodule_call_and_actions():
    a = ToyAgent()
    # autodiscovered actions
    assert "greet" in a.actions
    assert callable(a.actions["greet"]) is True

    # __call__ schedules forward through executor and returns a Future
    fut = a(1)
    res = await fut
    assert res == 2


def test_agentmodule_register_action_validates():
    a = ToyAgent()
    with pytest.raises(ValueError):
        a.register_action("", lambda: None)


@pytest.mark.asyncio
async def test_agentmodule_multiple_actions():
    """Test agent module with multiple actions"""
    
    class MultiActionAgent(AgentModule):
        @agent_action
        async def action_one(self, x: int) -> int:
            return x + 1
            
        @agent_action
        async def action_two(self, x: str) -> str:
            return f"processed: {x}"
            
        @agent_action
        async def action_three(self, x: float, y: float) -> float:
            return x * y
            
        async def forward(self, x):
            return f"forward: {x}"
    
    agent = MultiActionAgent()
    
    # Test all actions are discovered
    assert len(agent.actions) == 3
    assert "action_one" in agent.actions
    assert "action_two" in agent.actions
    assert "action_three" in agent.actions
    
    # Test each action works
    result1 = await agent.actions["action_one"](5)
    assert result1 == 6
    
    result2 = await agent.actions["action_two"]("test")
    assert result2 == "processed: test"
    
    result3 = await agent.actions["action_three"](2.5, 4.0)
    assert result3 == 10.0


@pytest.mark.asyncio
async def test_agentmodule_action_with_complex_types():
    """Test agent actions with complex parameter types"""
    
    class ComplexAgent(AgentModule):
        @agent_action
        async def process_dict(self, data: dict) -> dict:
            return {"processed": data, "count": len(data)}
            
        @agent_action
        async def process_list(self, items: list) -> list:
            return [str(item).upper() for item in items]
            
        async def forward(self, x):
            return x
    
    agent = ComplexAgent()
    
    # Test dict processing
    input_dict = {"a": 1, "b": 2, "c": 3}
    result_dict = await agent.actions["process_dict"](input_dict)
    assert result_dict["processed"] == input_dict
    assert result_dict["count"] == 3
    
    # Test list processing
    input_list = ["hello", "world", 123]
    result_list = await agent.actions["process_list"](input_list)
    assert result_list == ["HELLO", "WORLD", "123"]


@pytest.mark.asyncio
async def test_agentmodule_action_error_handling():
    """Test agent action error handling"""
    
    class ErrorAgent(AgentModule):
        @agent_action
        async def failing_action(self, should_fail: bool) -> str:
            if should_fail:
                raise ValueError("Action failed as requested")
            return "success"
            
        async def forward(self, x):
            return x
    
    agent = ErrorAgent()
    
    # Test successful action
    result = await agent.actions["failing_action"](False)
    assert result == "success"
    
    # Test failing action
    with pytest.raises(ValueError, match="Action failed as requested"):
        await agent.actions["failing_action"](True)


@pytest.mark.asyncio
async def test_agentmodule_register_custom_action():
    """Test registering custom actions at runtime"""
    
    agent = ToyAgent()
    
    async def custom_action(x: int, y: int) -> int:
        return x + y
    
    # Register custom action
    agent.register_action("add", custom_action)
    
    # Test custom action is available
    assert "add" in agent.actions
    assert len(agent.actions) == 2  # greet + add
    
    # Test custom action works
    result = await agent.actions["add"](3, 4)
    assert result == 7


@pytest.mark.asyncio
async def test_agentmodule_forward_with_different_types():
    """Test forward method with different input types"""
    
    class TypedAgent(AgentModule):
        async def forward(self, x):
            if isinstance(x, int):
                return x * 2
            elif isinstance(x, str):
                return f"string: {x}"
            elif isinstance(x, dict):
                return {"processed": True, "original": x}
            else:
                return f"unknown type: {type(x).__name__}"
    
    agent = TypedAgent()
    
    # Test different input types
    int_result = await agent(5)
    assert int_result == 10
    
    str_result = await agent("test")
    assert str_result == "string: test"
    
    dict_result = await agent({"key": "value"})
    assert dict_result == {"processed": True, "original": {"key": "value"}}
    
    list_result = await agent([1, 2, 3])
    assert list_result == "unknown type: list"


def test_agentmodule_register_action_validation_edge_cases():
    """Test edge cases for action registration validation"""
    agent = ToyAgent()
    
    # Test with None name
    with pytest.raises(ValueError):
        agent.register_action(None, lambda: None)
    
    # Test with empty string name
    with pytest.raises(ValueError):
        agent.register_action("", lambda: None)
    
    # Test whitespace-only name (currently allowed by implementation)
    agent.register_action("   ", lambda: "whitespace")
    assert "   " in agent.actions
    
    # Test duplicate registration should work (override)
    def action1():
        return "first"
    
    def action2():
        return "second"
    
    agent.register_action("test_action", action1)
    agent.register_action("test_action", action2)  # Should override
    
    assert "test_action" in agent.actions
    assert agent.actions["test_action"] == action2


@pytest.mark.asyncio
async def test_agentmodule_concurrent_execution():
    """Test agent module handles concurrent calls properly"""
    
    class ConcurrentAgent(AgentModule):
        def __init__(self):
            super().__init__()
            self.call_count = 0
            self.lock = asyncio.Lock()
            
        async def forward(self, delay: float):
            async with self.lock:
                self.call_count += 1
                current_count = self.call_count
            await asyncio.sleep(delay)
            return current_count
    
    agent = ConcurrentAgent()
    
    # Start multiple concurrent calls
    futures = [
        agent(0.01),
        agent(0.01),
        agent(0.01)
    ]
    
    # Wait for all to complete
    results = await asyncio.gather(*futures)
    
    # Each call should have incremented the counter
    assert sorted(results) == [1, 2, 3]
