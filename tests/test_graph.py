"""
Tests for vagents.executor.graph module.
"""
import pytest
from vagents.executor.graph import Graph
from vagents.executor.node import ActionNode, ConditionNode, BreakNode, ReturnNode


class TestGraph:
    """Test the Graph class."""

    def test_graph_creation(self):
        """Test Graph creation."""
        entry_node = ActionNode("x = 1")
        graph = Graph(entry_node)

        assert graph.entry == entry_node

    def test_graph_creation_empty(self):
        """Test Graph creation with no entry node."""
        graph = Graph(None)

        assert graph.entry is None

    def test_graph_optimize(self):
        """Test graph optimization."""
        node2 = ActionNode("y = await func2()")
        node1 = ActionNode("x = await func1()", node2)
        graph = Graph(node1)

        optimized = graph.optimize()

        # Should apply optimizations
        assert isinstance(optimized, Graph)
        assert "asyncio.gather" in optimized.entry.source

    def test_graph_repr_empty(self):
        """Test Graph string representation with empty graph."""
        graph = Graph(None)
        repr_str = repr(graph)

        assert "Graph(<empty>)" in repr_str

    def test_graph_repr_single_node(self):
        """Test Graph string representation with single node."""
        node = ActionNode("x = 1")
        graph = Graph(node)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "ActionNode" in repr_str
        assert "x = 1" in repr_str
        assert "--next-->" in repr_str
        assert "<exit>" in repr_str

    def test_graph_repr_chain(self):
        """Test Graph string representation with node chain."""
        node3 = ActionNode("z = x + y")
        node2 = ActionNode("y = 2", node3)
        node1 = ActionNode("x = 1", node2)
        graph = Graph(node1)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "x = 1" in repr_str
        assert "y = 2" in repr_str
        assert "z = x + y" in repr_str
        assert "--next-->" in repr_str

    def test_graph_repr_condition_node(self):
        """Test Graph string representation with condition node."""
        true_node = ActionNode("result = 'true'")
        false_node = ActionNode("result = 'false'")
        condition = ConditionNode("x > 0", true_node, false_node)
        graph = Graph(condition)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "ConditionNode" in repr_str
        assert "x > 0" in repr_str
        assert "--true-->" in repr_str
        assert "--false-->" in repr_str

    def test_graph_repr_break_node(self):
        """Test Graph string representation with break node."""
        target = ActionNode("x = 1")
        break_node = BreakNode(target)
        graph = Graph(break_node)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "BreakNode" in repr_str
        assert "--target-->" in repr_str

    def test_graph_repr_return_node(self):
        """Test Graph string representation with return node."""
        return_node = ReturnNode("x + y")
        graph = Graph(return_node)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "ReturnNode" in repr_str
        assert "(returns: x + y)" in repr_str

    def test_graph_repr_return_node_no_value(self):
        """Test Graph string representation with return node without value."""
        return_node = ReturnNode()
        graph = Graph(return_node)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "ReturnNode" in repr_str
        assert "(returns: None)" in repr_str

    def test_graph_repr_cycles(self):
        """Test Graph string representation with cycles."""
        node1 = ActionNode("x = 1")
        node2 = ActionNode("x += 1", node1)  # Creates a cycle
        node1.next = node2
        graph = Graph(node1)
        repr_str = repr(graph)

        # Should handle cycles without infinite loops
        assert "Graph:" in repr_str
        assert "x = 1" in repr_str
        assert "x += 1" in repr_str

    def test_graph_repr_complex_structure(self):
        """Test Graph string representation with complex structure."""
        # Create a more complex graph structure
        action1 = ActionNode("x = 1")
        action2 = ActionNode("y = 2")
        action3 = ActionNode("z = x + y")

        condition = ConditionNode("x > 0", action2, action3)
        action1.next = condition

        graph = Graph(action1)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "x = 1" in repr_str
        assert "y = 2" in repr_str
        assert "z = x + y" in repr_str
        assert "x > 0" in repr_str
        assert "--true-->" in repr_str
        assert "--false-->" in repr_str

    def test_graph_repr_multiple_paths(self):
        """Test Graph string representation with multiple execution paths."""
        # Create a diamond-shaped graph
        end_node = ActionNode("print('end')")

        true_branch = ActionNode("left = True", end_node)
        false_branch = ActionNode("right = False", end_node)

        condition = ConditionNode("flag", true_branch, false_branch)
        start_node = ActionNode("flag = True", condition)

        graph = Graph(start_node)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "flag = True" in repr_str
        assert "left = True" in repr_str
        assert "right = False" in repr_str
        assert "print('end')" in repr_str

    def test_graph_repr_unknown_node_type(self):
        """Test Graph string representation with unknown node type."""
        from vagents.executor.node import Node

        class UnknownNode(Node):
            def __init__(self):
                super().__init__()

            async def execute(self, ctx):
                return None

        unknown_node = UnknownNode()
        graph = Graph(unknown_node)
        repr_str = repr(graph)

        assert "Graph:" in repr_str
        assert "Unknown node type" in repr_str
        assert "UnknownNode" in repr_str

    def test_graph_optimization_preserves_structure(self):
        """Test that optimization preserves graph structure for non-optimizable cases."""
        node = ActionNode("x = 5")
        graph = Graph(node)

        optimized = graph.optimize()

        assert optimized.entry == node
        assert optimized.entry.source == "x = 5"

    def test_graph_optimization_with_complex_chain(self):
        """Test optimization with complex node chain."""
        # Mix of await and non-await nodes
        node4 = ActionNode("print(result)")
        node3 = ActionNode("result = x + y", node4)
        node2 = ActionNode("y = await get_y()", node3)
        node1 = ActionNode("x = await get_x()", node2)

        graph = Graph(node1)
        optimized = graph.optimize()

        # Should optimize the first two await nodes
        assert "asyncio.gather" in optimized.entry.source
        assert "get_x(), get_y()" in optimized.entry.source

    def test_graph_multiple_optimizations_ready(self):
        """Test that graph is ready for multiple optimization passes."""
        node = ActionNode("x = await func()")
        graph = Graph(node)

        # Apply optimization multiple times
        optimized1 = graph.optimize()
        optimized2 = optimized1.optimize()

        # Should be stable after first optimization
        assert optimized1.entry.source == optimized2.entry.source


class TestGraphTraversal:
    """Test graph traversal and representation logic."""

    def test_graph_traversal_visits_all_nodes(self):
        """Test that graph representation visits all reachable nodes."""
        # Create a graph with multiple paths
        node_a = ActionNode("a = 1")
        node_b = ActionNode("b = 2")
        node_c = ActionNode("c = 3")
        node_d = ActionNode("d = 4")

        condition = ConditionNode("flag", node_b, node_c)
        node_a.next = condition
        node_b.next = node_d
        node_c.next = node_d

        graph = Graph(node_a)
        repr_str = repr(graph)

        # All nodes should be represented
        assert "a = 1" in repr_str
        assert "b = 2" in repr_str
        assert "c = 3" in repr_str
        assert "d = 4" in repr_str

    def test_graph_traversal_handles_unreachable_nodes(self):
        """Test that unreachable nodes are not included in representation."""
        reachable = ActionNode("reachable = 1")
        unreachable = ActionNode("unreachable = 2")  # Not connected to graph

        graph = Graph(reachable)
        repr_str = repr(graph)

        assert "reachable = 1" in repr_str
        assert "unreachable = 2" not in repr_str

    def test_graph_traversal_prevents_infinite_loops(self):
        """Test that graph traversal handles cycles without infinite loops."""
        # Create a simple cycle
        node1 = ActionNode("step1")
        node2 = ActionNode("step2")
        node3 = ActionNode("step3")

        node1.next = node2
        node2.next = node3
        node3.next = node1  # Creates cycle

        graph = Graph(node1)

        # Should not hang or crash
        repr_str = repr(graph)
        assert "step1" in repr_str
        assert "step2" in repr_str
        assert "step3" in repr_str

    def test_graph_node_id_uniqueness_in_repr(self):
        """Test that node IDs are unique in representation."""
        node1 = ActionNode("x = 1")
        node2 = ActionNode("y = 2")

        graph = Graph(node1)
        repr_str = repr(graph)

        # Should contain unique node IDs
        assert f"<{node1.id}>" in repr_str
        assert f"<{node2.id}>" not in repr_str  # Not reachable
