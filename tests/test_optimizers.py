"""
Tests for vagents.executor.optimizers module.
"""
import pytest
from vagents.executor.node import ActionNode
from vagents.executor.graph import Graph
from vagents.executor.optimizers import optimize_await_sequences, apply_optimizations


class TestOptimizeAwaitSequences:
    """Test the optimize_await_sequences function."""

    def test_single_await_no_optimization(self):
        """Test that a single await statement is not optimized."""
        node = ActionNode("result = await func()")
        graph = Graph(node)

        optimized_graph = optimize_await_sequences(graph)

        # Should not be modified since there's only one await
        assert optimized_graph.entry == node
        assert optimized_graph.entry.source == "result = await func()"

    def test_multiple_await_assignments_optimization(self):
        """Test that multiple consecutive await assignments are optimized."""
        # Create a chain of await assignments
        node3 = ActionNode("z = await func3()")
        node2 = ActionNode("y = await func2()", node3)
        node1 = ActionNode("x = await func1()", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # Should be combined into a single node
        assert optimized_graph.entry != node1
        assert "asyncio.gather" in optimized_graph.entry.source
        assert "func1(), func2(), func3()" in optimized_graph.entry.source
        assert "x, y, z = __results" in optimized_graph.entry.source

    def test_mixed_statements_partial_optimization(self):
        """Test optimization stops at non-await statements."""
        node3 = ActionNode("print('hello')")  # Non-await statement
        node2 = ActionNode("y = await func2()", node3)
        node1 = ActionNode("x = await func1()", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # Should optimize the first two await statements
        assert "asyncio.gather" in optimized_graph.entry.source
        assert "func1(), func2()" in optimized_graph.entry.source
        assert "x, y = __results" in optimized_graph.entry.source
        # Should point to the non-await statement
        assert optimized_graph.entry.next == node3

    def test_duplicate_variable_names_no_optimization(self):
        """Test that duplicate variable names prevent optimization."""
        node2 = ActionNode("x = await func2()")
        node1 = ActionNode("x = await func1()", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # Should not be optimized due to duplicate variable names
        assert optimized_graph.entry == node1

    def test_non_await_assignment_no_optimization(self):
        """Test that non-await assignments are not optimized."""
        node2 = ActionNode("y = 5")
        node1 = ActionNode("x = 3", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # Should not be modified
        assert optimized_graph.entry == node1

    def test_complex_await_expressions(self):
        """Test optimization with complex await expressions."""
        node2 = ActionNode("result2 = await client.request('POST', url, data=payload)")
        node1 = ActionNode("result1 = await api.fetch_data(id=123, timeout=30)", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # Should handle complex expressions
        assert "asyncio.gather" in optimized_graph.entry.source
        assert "api.fetch_data(id=123, timeout=30)" in optimized_graph.entry.source
        assert (
            "client.request('POST', url, data=payload)" in optimized_graph.entry.source
        )

    def test_typed_await_assignments(self):
        """Test optimization with type-annotated assignments."""
        node2 = ActionNode("y: int = await get_number()")
        node1 = ActionNode("x: str = await get_string()", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # Should optimize despite type annotations
        assert "asyncio.gather" in optimized_graph.entry.source
        assert "get_string(), get_number()" in optimized_graph.entry.source
        assert "x, y = __results" in optimized_graph.entry.source

    def test_empty_graph(self):
        """Test optimization with empty graph."""
        graph = Graph(None)

        optimized_graph = optimize_await_sequences(graph)

        # Should handle empty graph gracefully
        assert optimized_graph.entry is None

    def test_non_action_node_handling(self):
        """Test that non-ActionNode types are handled correctly."""
        from vagents.executor.node import Node

        class CustomNode(Node):
            def __init__(self):
                super().__init__()

            def execute(self, ctx):
                pass

        custom_node = CustomNode()
        graph = Graph(custom_node)

        optimized_graph = optimize_await_sequences(graph)

        # Should not modify non-ActionNode entries
        assert optimized_graph.entry == custom_node


class TestApplyOptimizations:
    """Test the apply_optimizations function."""

    def test_apply_optimizations_calls_await_optimization(self):
        """Test that apply_optimizations calls the await sequence optimizer."""
        node2 = ActionNode("y = await func2()")
        node1 = ActionNode("x = await func1()", node2)
        graph = Graph(node1)

        optimized_graph = apply_optimizations(graph)

        # Should have applied await sequence optimization
        assert "asyncio.gather" in optimized_graph.entry.source

    def test_apply_optimizations_preserves_graph_structure(self):
        """Test that apply_optimizations preserves non-optimizable parts."""
        node = ActionNode("x = 5")
        graph = Graph(node)

        optimized_graph = apply_optimizations(graph)

        # Should preserve the original structure
        assert optimized_graph.entry == node

    def test_optimization_chaining_ready(self):
        """Test that the optimization system is ready for chaining multiple optimizers."""
        node = ActionNode("x = await func()")
        graph = Graph(node)

        # This test ensures the structure supports future optimizer chaining
        optimized_graph = apply_optimizations(graph)

        # Should return a valid graph object
        assert isinstance(optimized_graph, Graph)
        assert optimized_graph.entry is not None


@pytest.mark.asyncio
class TestOptimizationIntegration:
    """Integration tests for the optimization system."""

    async def test_optimized_await_sequence_execution(self):
        """Test that optimized await sequences can be executed."""
        # This is more of an integration test to ensure optimized code is valid
        node2 = ActionNode("y = await asyncio.sleep(0.01, result=2)")
        node1 = ActionNode("x = await asyncio.sleep(0.01, result=1)", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # The optimized code should be syntactically valid
        import ast

        try:
            ast.parse(optimized_graph.entry.source)
        except SyntaxError:
            pytest.fail("Optimized code is not syntactically valid")

    def test_optimization_preserves_semantics(self):
        """Test that optimization preserves the semantic meaning."""
        # Create nodes that would benefit from optimization
        node3 = ActionNode("c = await get_value(3)")
        node2 = ActionNode("b = await get_value(2)", node3)
        node1 = ActionNode("a = await get_value(1)", node2)
        graph = Graph(node1)

        optimized_graph = optimize_await_sequences(graph)

        # The optimized version should assign to the same variables
        source = optimized_graph.entry.source
        assert "a, b, c = __results" in source
        assert "get_value(1), get_value(2), get_value(3)" in source
