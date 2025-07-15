"""
Tests for vagents.executor.builder module.
"""
import pytest
import ast
from vagents.executor.builder import GraphBuilder
from vagents.executor.node import ActionNode, ConditionNode, ReturnNode, BreakNode
from vagents.executor.graph import Graph


class TestGraphBuilder:
    """Test the GraphBuilder class."""

    def test_graph_builder_initialization(self):
        """Test GraphBuilder initialization."""
        builder = GraphBuilder()

        assert builder.lines == []
        assert builder.indent_map == {}
        assert builder.loop_stack == []

    def test_build_simple_assignment(self):
        """Test building graph from simple assignment."""
        builder = GraphBuilder()
        source = "x = 5"

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_function_definition(self):
        """Test building graph from function definition."""
        builder = GraphBuilder()
        source = """
        def test_func():
            x = 1
            y = 2
            return x + y
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_async_function_definition(self):
        """Test building graph from async function definition."""
        builder = GraphBuilder()
        source = """
        async def async_func():
            x = await some_async_call()
            return x
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_conditional_statement(self):
        """Test building graph with conditional statement."""
        builder = GraphBuilder()
        source = """
        if x > 0:
            y = x * 2
        else:
            y = 0
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_loop_statement(self):
        """Test building graph with loop statement."""
        builder = GraphBuilder()
        source = """
        for i in range(10):
            x = i * 2
            if x > 10:
                break
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_while_loop(self):
        """Test building graph with while loop."""
        builder = GraphBuilder()
        source = """
        while x < 10:
            x = x + 1
            if x == 5:
                continue
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_nested_conditions(self):
        """Test building graph with nested conditions."""
        builder = GraphBuilder()
        source = """
        if x > 0:
            if y > 0:
                z = x + y
            else:
                z = x - y
        else:
            z = 0
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_try_except_block(self):
        """Test building graph with try-except block."""
        builder = GraphBuilder()
        source = """
        try:
            x = risky_operation()
        except ValueError:
            x = default_value
        finally:
            cleanup()
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_return_statement(self):
        """Test building graph with return statement."""
        builder = GraphBuilder()
        source = """
        x = 5
        if x > 3:
            return x
        y = x + 1
        return y
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_break_statement(self):
        """Test building graph with break statement."""
        builder = GraphBuilder()
        source = """
        for i in range(10):
            if i == 5:
                break
            x = i * 2
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_continue_statement(self):
        """Test building graph with continue statement."""
        builder = GraphBuilder()
        source = """
        for i in range(10):
            if i % 2 == 0:
                continue
            x = i * 2
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_yield_statement(self):
        """Test building graph with yield statement."""
        builder = GraphBuilder()
        source = """
        def generator():
            for i in range(5):
                yield i
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_empty_source(self):
        """Test building graph from empty source."""
        builder = GraphBuilder()
        source = ""

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        # Should have at least a return node
        assert graph.entry is not None

    def test_build_comment_only_source(self):
        """Test building graph from source with only comments."""
        builder = GraphBuilder()
        source = """
        # This is a comment
        # Another comment
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_mixed_indentation(self):
        """Test building graph with mixed indentation levels."""
        builder = GraphBuilder()
        source = """
        x = 1
        if x > 0:
            y = 2
            if y > 1:
                z = 3
            else:
                z = 1
        else:
            y = 0
        result = x + y + z
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_indent_map_creation(self):
        """Test that indent_map is created correctly."""
        builder = GraphBuilder()
        source = """
x = 1
if True:
    y = 2
    if True:
        z = 3
    a = 4
b = 5
        """

        graph = builder.build(source)

        # Verify indent_map was created
        assert len(builder.indent_map) > 0
        assert all(isinstance(v, int) for v in builder.indent_map.values())

    def test_build_with_class_definition(self):
        """Test building graph with class definition."""
        builder = GraphBuilder()
        source = """
        class TestClass:
            def __init__(self):
                self.x = 1

            def method(self):
                return self.x
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_multiple_functions(self):
        """Test building graph with multiple function definitions."""
        builder = GraphBuilder()
        source = """
        def func1():
            return 1

        def func2():
            return 2

        x = func1() + func2()
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_comprehensions(self):
        """Test building graph with list/dict comprehensions."""
        builder = GraphBuilder()
        source = """
        numbers = [i for i in range(10) if i % 2 == 0]
        squares = {i: i**2 for i in numbers}
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_lambda(self):
        """Test building graph with lambda functions."""
        builder = GraphBuilder()
        source = """
        add = lambda x, y: x + y
        result = add(5, 3)
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_imports(self):
        """Test building graph with import statements."""
        builder = GraphBuilder()
        source = """
        import os
        from sys import path
        x = os.getcwd()
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_global_statement(self):
        """Test building graph with global statement."""
        builder = GraphBuilder()
        source = """
        def func():
            global x
            x = 10
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_nonlocal_statement(self):
        """Test building graph with nonlocal statement."""
        builder = GraphBuilder()
        source = """
        def outer():
            x = 1
            def inner():
                nonlocal x
                x = 2
            inner()
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_assert_statement(self):
        """Test building graph with assert statement."""
        builder = GraphBuilder()
        source = """
        x = 5
        assert x > 0, "x must be positive"
        y = x * 2
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_with_raise_statement(self):
        """Test building graph with raise statement."""
        builder = GraphBuilder()
        source = """
        x = -1
        if x < 0:
            raise ValueError("Negative value")
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_build_complex_control_flow(self):
        """Test building graph with complex control flow."""
        builder = GraphBuilder()
        source = """
        def complex_function(data):
            result = []
            for item in data:
                try:
                    if item > 0:
                        for i in range(item):
                            if i % 2 == 0:
                                result.append(i)
                            else:
                                continue
                    elif item == 0:
                        break
                    else:
                        raise ValueError("Negative item")
                except ValueError as e:
                    print(f"Error: {e}")
                    continue
                finally:
                    print("Processing complete")
            return result
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        assert graph.entry is not None

    def test_loop_stack_management(self):
        """Test that loop_stack is managed correctly during building."""
        builder = GraphBuilder()
        source = """
        for i in range(3):
            for j in range(3):
                if i == j:
                    break
        """

        graph = builder.build(source)

        assert isinstance(graph, Graph)
        # Loop stack should be empty after building
        assert len(builder.loop_stack) == 0
