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
        self.source = source.strip("\n")
        self.code = self.source
        self.next = next_node

    def execute(self, ctx):
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
        return f"ActionNode<{self.id}>({self.code})"


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
        return f"ReturnNode<{self.id}>({self.id})"
