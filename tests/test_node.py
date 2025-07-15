"""
Tests for vagents.executor.node module.
"""
import pytest
import asyncio
from vagents.executor.node import (
    Node,
    ActionNode,
    ConditionNode,
    BreakNode,
    ReturnNode,
    YieldNode,
)


class TestNode:
    """Test the base Node class."""

    def test_node_id_generation(self):
        """Test that nodes get unique IDs."""
        node1 = ActionNode("x = 1")
        node2 = ActionNode("y = 2")

        assert node1.id != node2.id
        assert isinstance(node1.id, int)
        assert isinstance(node2.id, int)

    def test_node_abstract_execute(self):
        """Test that base Node class has abstract execute method."""
        node = Node()

        with pytest.raises(NotImplementedError):
            node.execute({})


class TestActionNode:
    """Test the ActionNode class."""

    def test_action_node_creation(self):
        """Test ActionNode creation and basic properties."""
        source = "x = 5"
        node = ActionNode(source)

        assert node.source == source
        assert node.code == source
        assert node.next is None

    def test_action_node_with_next(self):
        """Test ActionNode with next node."""
        next_node = ActionNode("y = 10")
        node = ActionNode("x = 5", next_node)

        assert node.next == next_node

    def test_action_node_source_stripping(self):
        """Test that source code is properly stripped."""
        node = ActionNode("  x = 5  ")
        assert node.source == "x = 5"

    @pytest.mark.asyncio
    async def test_action_node_simple_execution(self):
        """Test simple synchronous execution."""
        node = ActionNode("x = 5")
        ctx = {}

        result = await node.execute(ctx)

        assert ctx["x"] == 5
        assert result == node.next

    @pytest.mark.asyncio
    async def test_action_node_await_assignment(self):
        """Test await assignment execution."""

        async def mock_func():
            return 42

        node = ActionNode("result = await mock_func()")
        ctx = {"mock_func": mock_func}

        result = await node.execute(ctx)

        assert ctx["result"] == 42
        assert result == node.next

    @pytest.mark.asyncio
    async def test_action_node_typed_await_assignment(self):
        """Test typed await assignment execution."""

        async def mock_func():
            return "hello"

        node = ActionNode("result: str = await mock_func()")
        ctx = {"mock_func": mock_func}

        result = await node.execute(ctx)

        assert ctx["result"] == "hello"
        assert result == node.next

    @pytest.mark.asyncio
    async def test_action_node_complex_await_expression(self):
        """Test complex await expression."""

        async def mock_api_call(endpoint, data):
            return f"Response from {endpoint} with {data}"

        node = ActionNode(
            "response = await mock_api_call('/api/test', {'key': 'value'})"
        )
        ctx = {"mock_api_call": mock_api_call}

        result = await node.execute(ctx)

        assert "Response from /api/test" in ctx["response"]
        assert result == node.next

    @pytest.mark.asyncio
    async def test_action_node_await_without_assignment(self):
        """Test await statement without assignment."""

        async def mock_func():
            return "side effect"

        node = ActionNode("await mock_func()")
        ctx = {"mock_func": mock_func, "side_effect": None}

        result = await node.execute(ctx)

        # Should execute without error
        assert result == node.next

    def test_action_node_repr(self):
        """Test ActionNode string representation."""
        node = ActionNode("x = 5")
        repr_str = repr(node)

        assert "ActionNode" in repr_str
        assert str(node.id) in repr_str
        assert "x = 5" in repr_str


class TestConditionNode:
    """Test the ConditionNode class."""

    def test_condition_node_creation(self):
        """Test ConditionNode creation."""
        true_node = ActionNode("x = 1")
        false_node = ActionNode("x = 0")
        condition = ConditionNode("x > 0", true_node, false_node)

        assert condition.test_source == "x > 0"
        assert condition.code == "x > 0"
        assert condition.true_next == true_node
        assert condition.false_next == false_node

    @pytest.mark.asyncio
    async def test_condition_node_true_branch(self):
        """Test condition node taking true branch."""
        true_node = ActionNode("result = 'true'")
        false_node = ActionNode("result = 'false'")
        condition = ConditionNode("x > 0", true_node, false_node)

        ctx = {"x": 5}
        result = await condition.execute(ctx)

        assert result == true_node

    @pytest.mark.asyncio
    async def test_condition_node_false_branch(self):
        """Test condition node taking false branch."""
        true_node = ActionNode("result = 'true'")
        false_node = ActionNode("result = 'false'")
        condition = ConditionNode("x > 0", true_node, false_node)

        ctx = {"x": -5}
        result = await condition.execute(ctx)

        assert result == false_node

    @pytest.mark.asyncio
    async def test_condition_node_complex_expression(self):
        """Test condition node with complex expression."""
        true_node = ActionNode("result = 'complex_true'")
        false_node = ActionNode("result = 'complex_false'")
        condition = ConditionNode(
            "len(data) > 2 and data[0] == 'test'", true_node, false_node
        )

        ctx = {"data": ["test", "more", "data"]}
        result = await condition.execute(ctx)

        assert result == true_node

    def test_condition_node_repr(self):
        """Test ConditionNode string representation."""
        condition = ConditionNode("x > 0")
        repr_str = repr(condition)

        assert "ConditionNode" in repr_str
        assert str(condition.id) in repr_str
        assert "x > 0" in repr_str


class TestBreakNode:
    """Test the BreakNode class."""

    def test_break_node_creation(self):
        """Test BreakNode creation."""
        target = ActionNode("x = 1")
        break_node = BreakNode(target)

        assert break_node.target == target

    @pytest.mark.asyncio
    async def test_break_node_execution(self):
        """Test BreakNode execution."""
        target = ActionNode("x = 1")
        break_node = BreakNode(target)

        ctx = {}
        result = await break_node.execute(ctx)

        assert result == target

    def test_break_node_repr(self):
        """Test BreakNode string representation."""
        target = ActionNode("x = 1")
        break_node = BreakNode(target)
        repr_str = repr(break_node)

        assert "BreakNode" in repr_str
        assert str(break_node.id) in repr_str


class TestReturnNode:
    """Test the ReturnNode class."""

    def test_return_node_creation_with_value(self):
        """Test ReturnNode creation with return value."""
        return_node = ReturnNode("x + y")

        assert return_node.value_source == "x + y"
        assert return_node.code is not None

    def test_return_node_creation_without_value(self):
        """Test ReturnNode creation without return value."""
        return_node = ReturnNode()

        assert return_node.value_source is None
        assert return_node.code is None

    @pytest.mark.asyncio
    async def test_return_node_execution_with_value(self):
        """Test ReturnNode execution with return value."""
        return_node = ReturnNode("x + y")

        ctx = {"x": 5, "y": 3}
        result = await return_node.execute(ctx)

        assert result == 8

    @pytest.mark.asyncio
    async def test_return_node_execution_without_value(self):
        """Test ReturnNode execution without return value."""
        return_node = ReturnNode()

        ctx = {}
        result = await return_node.execute(ctx)

        assert result is None

    @pytest.mark.asyncio
    async def test_return_node_complex_expression(self):
        """Test ReturnNode with complex expression."""
        return_node = ReturnNode("max(data) if data else 0")

        ctx = {"data": [1, 5, 3, 9, 2]}
        result = await return_node.execute(ctx)

        assert result == 9

    def test_return_node_repr(self):
        """Test ReturnNode string representation."""
        return_node = ReturnNode("x + y")
        repr_str = repr(return_node)

        assert "ReturnNode" in repr_str
        assert str(return_node.id) in repr_str
        assert "x + y" in repr_str


class TestYieldNode:
    """Test the YieldNode class."""

    def test_yield_node_creation(self):
        """Test YieldNode creation."""
        next_node = ActionNode("x += 1")
        yield_node = YieldNode("x", next_node)

        assert yield_node.yield_expression_source == "x"
        assert yield_node.next == next_node
        assert yield_node.is_generator is True

    @pytest.mark.asyncio
    async def test_yield_node_execution(self):
        """Test YieldNode execution."""
        yield_node = YieldNode("x * 2")

        ctx = {"x": 5}
        result_generator = yield_node.execute(ctx)

        # Should be an async generator
        assert hasattr(result_generator, "__anext__")

        # Get the yielded value
        yielded_value = await result_generator.__anext__()
        assert yielded_value == 10

        # Should be exhausted after one yield
        with pytest.raises(StopAsyncIteration):
            await result_generator.__anext__()

    @pytest.mark.asyncio
    async def test_yield_node_complex_expression(self):
        """Test YieldNode with complex expression."""
        yield_node = YieldNode("sum(data) if data else 0")

        ctx = {"data": [1, 2, 3, 4, 5]}
        result_generator = yield_node.execute(ctx)

        yielded_value = await result_generator.__anext__()
        assert yielded_value == 15

    def test_yield_node_repr(self):
        """Test YieldNode string representation."""
        yield_node = YieldNode("x * 2")
        repr_str = repr(yield_node)

        assert "YieldNode" in repr_str
        assert str(yield_node.id) in repr_str
        assert "yield x * 2" in repr_str


@pytest.mark.asyncio
class TestNodeChaining:
    """Test node chaining and execution flow."""

    async def test_action_node_chain(self):
        """Test chaining multiple ActionNodes."""
        node3 = ActionNode("z = x + y")
        node2 = ActionNode("y = 10", node3)
        node1 = ActionNode("x = 5", node2)

        ctx = {}

        # Execute the chain
        current = node1
        while current:
            current = await current.execute(ctx)

        assert ctx["x"] == 5
        assert ctx["y"] == 10
        assert ctx["z"] == 15

    async def test_condition_with_actions(self):
        """Test condition node with action nodes."""
        true_action = ActionNode("result = 'positive'")
        false_action = ActionNode("result = 'negative'")
        condition = ConditionNode("x > 0", true_action, false_action)

        # Test positive case
        ctx = {"x": 5}
        next_node = await condition.execute(ctx)
        assert next_node == true_action

        # Test negative case
        ctx = {"x": -5}
        next_node = await condition.execute(ctx)
        assert next_node == false_action
