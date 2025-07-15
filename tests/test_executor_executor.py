"""
Tests for vagents.executor.executor module.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from vagents.executor.executor import GraphExecutor, has_next
from vagents.executor.graph import Graph
from vagents.executor.node import ActionNode, ReturnNode


class TestGraphExecutor:
    """Test the GraphExecutor class."""

    def test_executor_initialization(self):
        """Test GraphExecutor initialization with basic parameters."""
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph

        executor = GraphExecutor(mock_graph)

        assert executor.graph == mock_graph
        assert executor.module_instance is None
        assert "__builtins__" in executor.base_ctx
        assert "has_next" in executor.base_ctx

    def test_executor_initialization_with_module(self):
        """Test GraphExecutor initialization with module instance."""
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph

        class MockModule:
            def __init__(self):
                self.test_attr = "test_value"

        module_instance = MockModule()
        executor = GraphExecutor(mock_graph, module_instance=module_instance)

        assert executor.module_instance == module_instance
        assert executor.base_ctx["self"] == module_instance
        assert executor.base_ctx["test_attr"] == "test_value"

    def test_executor_initialization_with_global_context(self):
        """Test GraphExecutor initialization with global context."""
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph

        global_context = {"custom_var": "custom_value"}
        executor = GraphExecutor(mock_graph, global_context=global_context)

        assert executor.base_ctx["custom_var"] == "custom_value"

    @pytest.mark.asyncio
    async def test_run_with_return_node(self):
        """Test running executor with a simple return node."""
        # Create a mock return node
        return_node = ReturnNode()
        return_node.code = "'test_result'"

        # Create a mock graph with the return node as entry
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph
        mock_graph.entry = return_node

        executor = GraphExecutor(mock_graph)
        inputs = ["test_input"]

        results = []
        async for result in executor.run(inputs):
            results.append(result)

        assert len(results) == 1
        assert results[0] == "test_result"

    @pytest.mark.asyncio
    async def test_run_with_action_node(self):
        """Test running executor with action node."""
        # Create mock nodes
        action_node = MagicMock()
        action_node.is_generator = False
        action_node.execute = AsyncMock()

        return_node = ReturnNode()
        return_node.code = "'final_result'"

        action_node.execute.return_value = return_node

        # Create mock graph
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph
        mock_graph.entry = action_node

        executor = GraphExecutor(mock_graph)
        inputs = ["test_input"]

        results = []
        async for result in executor.run(inputs):
            results.append(result)

        assert len(results) == 1
        assert results[0] == "final_result"
        action_node.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_generator_node(self):
        """Test running executor with generator node."""

        async def mock_generator():
            yield "result1"
            yield "result2"

        # Create mock generator node
        generator_node = MagicMock()
        generator_node.is_generator = True
        generator_node.execute = MagicMock(return_value=mock_generator())
        generator_node.next = None

        # Create mock graph
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph
        mock_graph.entry = generator_node

        executor = GraphExecutor(mock_graph)
        inputs = ["test_input"]

        results = []
        async for result in executor.run(inputs):
            results.append(result)

        assert len(results) == 2
        assert results[0] == "result1"
        assert results[1] == "result2"

    @pytest.mark.asyncio
    async def test_run_with_multiple_inputs(self):
        """Test running executor with multiple inputs."""
        # Create a simple return node
        return_node = ReturnNode()
        return_node.code = "query + '_processed'"

        # Create mock graph
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph
        mock_graph.entry = return_node

        executor = GraphExecutor(mock_graph)
        inputs = ["input1", "input2"]

        results = []
        async for result in executor.run(inputs):
            results.append(result)

        assert len(results) == 2
        assert results[0] == "input1_processed"
        assert results[1] == "input2_processed"

    @pytest.mark.asyncio
    async def test_run_with_yield_tuple(self):
        """Test running executor with yield tuple from node."""
        # Create mock action node that returns yield tuple
        action_node = MagicMock()
        action_node.is_generator = False
        action_node.execute = AsyncMock()
        action_node.execute.return_value = ("YIELD", "yielded_value", None)

        # Create mock graph
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph
        mock_graph.entry = action_node

        executor = GraphExecutor(mock_graph)
        inputs = ["test_input"]

        results = []
        async for result in executor.run(inputs):
            results.append(result)

        assert len(results) == 1
        assert results[0] == "yielded_value"

    def test_run_with_empty_inputs(self):
        """Test running executor with empty inputs."""
        mock_graph = MagicMock()
        mock_graph.optimize.return_value = mock_graph

        executor = GraphExecutor(mock_graph)

        # Should handle empty inputs gracefully
        async def test_empty():
            results = []
            async for result in executor.run([]):
                results.append(result)
            return results

        results = asyncio.run(test_empty())
        assert len(results) == 0


class TestHasNext:
    """Test the has_next function."""

    def test_has_next_with_elements(self):
        """Test has_next when iterator has elements."""
        context = {"test_iter": iter([1, 2, 3])}

        result = has_next("test_iter", context)

        assert result is True
        # Check that the first element is preserved
        assert next(context["test_iter"]) == 1

    def test_has_next_empty_iterator(self):
        """Test has_next when iterator is empty."""
        context = {"test_iter": iter([])}

        result = has_next("test_iter", context)

        assert result is False

    def test_has_next_missing_iterator(self):
        """Test has_next when iterator doesn't exist in context."""
        context = {}

        with pytest.raises(NameError, match="Iterator 'missing_iter' not found"):
            has_next("missing_iter", context)

    def test_has_next_non_iterator(self):
        """Test has_next when context value is not an iterator."""
        context = {"not_iter": "string_value"}

        result = has_next("not_iter", context)

        assert result is False

    def test_has_next_preserves_all_elements(self):
        """Test that has_next preserves all elements in correct order."""
        original_data = [1, 2, 3, 4]
        context = {"test_iter": iter(original_data)}

        # Check has_next
        result = has_next("test_iter", context)
        assert result is True

        # Consume all elements and verify order
        consumed = list(context["test_iter"])
        assert consumed == original_data
