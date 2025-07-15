import re
from .node import ActionNode


def optimize_await_sequences(graph):
    """
    Detect consecutive independent await assignments and collapse them into a single asyncio.gather call.
    """
    head = graph.entry
    seq = []
    cur = head
    # Collect sequential await assignments
    while isinstance(cur, ActionNode):
        # Handle both simple assignments and type-annotated assignments
        # Pattern matches: var = await expr OR var: type = await expr
        m = re.match(r"(\w+)(?:\s*:\s*\w+)?\s*=\s*await\s+(.+)", cur.source)
        if not m:
            break
        var, expr = m.groups()
        seq.append((cur, var, expr))
        cur = cur.next
    # Only combine if more than one and variables are unique
    vars_seq = [var for _, var, _ in seq]
    if len(seq) > 1 and len(set(vars_seq)) == len(seq):
        exprs = ", ".join(expr for _, _, expr in seq)
        vars_list = ", ".join(var for _, var, _ in seq)
        combined_src = (
            "import asyncio\n"
            f"__results = await asyncio.gather({exprs})\n"
            f"{vars_list} = __results"
        )
        new_node = ActionNode(combined_src, cur)
        graph.entry = new_node
    return graph


def apply_optimizations(graph):
    """
    Apply all registered graph optimizations in sequence.
    """
    graph = optimize_await_sequences(graph)
    # future optimizers can be chained here
    return graph
