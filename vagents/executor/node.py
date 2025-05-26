import ast
import asyncio
from vagents.core import OutResponse

class Node:
    """Base class for all executable graph nodes."""

    _id_counter = 0

    def __init__(self):
        self.id = Node._id_counter
        Node._id_counter += 1

    def execute(self, ctx):
        raise NotImplementedError


class ActionNode(Node):
    """Sequential statement (assignment, call, definition, …)."""

    def __init__(self, source: str, next_node=None):
        super().__init__()
        self.source = source.strip()  # Changed from source.strip("\\n")
        self.code = self.source
        self.next = next_node

    def execute(self, ctx):
        # If this statement contains an await, handle awaited assignment or fallback
        if 'await ' in self.source:
            import re
            # Regex to match patterns like 'var = await expr' or 'var: type = await expr'
            m = re.match(r"(\w+)\s*(?::\s*\w+)?\s*=\s*await\s+(.+)", self.source)
            if m:
                var, expr = m.groups()
                # Build coroutine that returns the awaited expression
                async_code = f"async def __node_exec():\n    return await {expr}"
                exec(async_code, ctx, ctx)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                result = loop.run_until_complete(ctx["__node_exec"]())
                del ctx["__node_exec"]
                # Store result back into context
                ctx[var] = result
                return self.next
            # Fallback for other await statements
            async_code = "async def __node_exec():\n    " + self.source
            exec(async_code, ctx, ctx)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(ctx["__node_exec"]())
            del ctx["__node_exec"]
            return self.next
        # Normal synchronous execution
        exec(self.code, ctx, ctx)
        return self.next

    def __repr__(self):
        return f"ActionNode<{self.id}>({self.source})"


class ConditionNode(Node):
    """Boolean test that chooses the next node."""

    def __init__(self, test_source: str, true_next=None, false_next=None):
        super().__init__()
        self.test_source = test_source.strip("\n")
        self.code = test_source
        self.true_next = true_next
        self.false_next = false_next

    def execute(self, ctx):
        branch = eval(self.code, ctx, ctx)
        return self.true_next if branch else self.false_next

    def __repr__(self):
        return f"ConditionNode<{self.id}>({self.code})"


class BreakNode(Node):
    """Represents a direct jump (`break`/`continue`)."""

    def __init__(self, target):
        super().__init__()
        self.target = target

    def execute(self, ctx):
        return self.target

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.id}>({self.target})"


class ReturnNode(Node):
    """Represents a `return` statement inside a function.

    When executed it:
      • Evaluates the return expression (if any) into ``ctx['__return__']``
      • Terminates graph execution by returning ``None``.
    """

    def __init__(self, value_source: str | None = None):
        super().__init__()
        self.value_source = value_source.strip("\n") if value_source else None
        self.code = (
            compile(self.value_source, f"<return:{self.id}>", "eval")
            if self.value_source
            else None
        )

    def execute(self, ctx):
        ctx["__return__"] = eval(self.code, ctx, ctx) if self.code else None
        return None  # stop execution

    def __repr__(self):
        return f"ReturnNode<{self.id}>({self.value_source})"


class YieldNode(Node):
    """Represents a `yield` statement."""

    def __init__(self, yield_expression_source: str, next_node=None):
        super().__init__()
        self.yield_expression_source = yield_expression_source.strip()
        self.next = next_node

    def execute(self, ctx):
        # Define a temporary async generator that yields the single expression
        async_code = f"async def __node_exec():\n    yield {self.yield_expression_source}"
        exec(async_code, ctx, ctx)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        generator_instance = ctx["__node_exec"]()
        del ctx["__node_exec"] # Clean up temporary function from context

        try:
            # Run the generator to get its first (and in this wrapper, only) yielded value
            yielded_value = loop.run_until_complete(generator_instance.__anext__())
            
            # Make the yielded value available to the executor via a conventional context key
            if "__yielded_values_stream__" not in ctx:
                ctx["__yielded_values_stream__"] = []
            ctx["__yielded_values_stream__"].append(yielded_value)
            
        except StopAsyncIteration:
            # This would happen if the wrapped expression somehow didn't yield,
            # which is unlikely for 'yield some_expression'.
            pass 
        
        return self.next # Proceed to the next node in the graph

    def __repr__(self):
        return f"YieldNode<{self.id}>(yield {self.yield_expression_source})"
