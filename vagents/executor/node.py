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

    async def execute(self, ctx): # Changed to async def
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
                # No explicit loop management needed when called from an async GraphExecutor.run
                result = await ctx["__node_exec"]() # Directly await
                del ctx["__node_exec"]
                # Store result back into context
                ctx[var] = result
                return self.next
            # Fallback for other await statements
            async_code = "async def __node_exec():\n    " + self.source
            exec(async_code, ctx, ctx)
            await ctx["__node_exec"]() # Directly await
            del ctx["__node_exec"]
            return self.next
        # Normal synchronous execution (if no await)
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

    async def execute(self, ctx): # Changed to async def
        # Eval can remain synchronous if the test_source itself doesn't involve async calls
        # If test_source could be async, this would need more complex handling (e.g. ast parsing)
        branch = eval(self.code, ctx, ctx)
        return self.true_next if branch else self.false_next

    def __repr__(self):
        return f"ConditionNode<{self.id}>({self.code})"


class BreakNode(Node):
    """Represents a direct jump (`break`/`continue`)."""

    def __init__(self, target):
        super().__init__()
        self.target = target

    async def execute(self, ctx): # Changed to async def
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

    async def execute(self, ctx): # Changed to async def
        # This will be yielded by GraphExecutor.run, not put in ctx['__return__'] for yielding
        return eval(self.code, ctx, ctx) if self.code else None

    def __repr__(self):
        return f"ReturnNode<{self.id}>({self.value_source})"


class YieldNode(Node):
    """Represents a `yield` statement."""

    def __init__(self, yield_expression_source: str, next_node=None):
        super().__init__()
        self.yield_expression_source = yield_expression_source.strip()
        self.next = next_node
        self.is_generator = True # Mark this node as one that yields multiple values

    async def execute(self, ctx): # Changed to async def, and now an async generator
        # Define a temporary async function that evaluates the expression to be yielded.
        # This is safer than direct eval if the expression itself could be complex.
        async_eval_code = f"async def __eval_yield_expr():\n    return {self.yield_expression_source}"
        exec(async_eval_code, ctx, ctx)
        
        yielded_value = await ctx["__eval_yield_expr"]() # Evaluate the expression
        del ctx["__eval_yield_expr"] # Clean up

        yield yielded_value # Yield the evaluated value
        
        # For the graph to continue, the YieldNode must indicate what the next node is.
        # However, a single YieldNode in a graph might be part of a loop, and the graph structure handles the next step.
        # The GraphExecutor.run loop will take care of moving to self.next if this node doesn't change control flow.
        # This execute method now yields the value and then implicitly finishes its turn.
        # The GraphExecutor will then proceed to self.next if this node is not a terminal node.
        # To be more explicit, we can return self.next, but GraphExecutor.run needs to handle it.
        # For now, let GraphExecutor.run handle moving to self.next based on the graph structure.
        # The key is that this method now `yields` the value.
        # To allow the graph to continue, this node should also return the next node.
        # This is a bit of a change in how GraphExecutor.run will work with generator nodes.
        # Let's assume for now that GraphExecutor.run will handle getting the next node from self.next
        # after this generator is exhausted (which it will be, after one yield).

    def __repr__(self):
        return f"YieldNode<{self.id}>(yield {self.yield_expression_source})"
