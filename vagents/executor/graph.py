from collections import deque
from .node import ActionNode, ConditionNode, BreakNode, ReturnNode
from .optimizers import apply_optimizations


class Graph:
    def __init__(self, entry):
        self.entry = entry

    def optimize(self):
        return apply_optimizations(self)

    def __repr__(self):
        if self.entry is None:
            return "Graph(<empty>)"

        lines = ["Graph:"]
        # Keep track of nodes whose details (label and outgoing edges) have been printed
        processed_nodes = set()

        queue = deque()
        if self.entry:
            queue.append(self.entry)

        while queue:
            node = queue.popleft()

            if (
                node is None
            ):  # Should not happen if None is not added, but as a safeguard
                continue

            # If this node's details have already been printed, skip it.
            # This handles cycles and ensures each node's section is printed only once.
            if node.id in processed_nodes:
                continue

            processed_nodes.add(node.id)
            lines.append(
                f"  {node}:"
            )  # Assumes all Node subclasses use/inherit label()

            # Helper to add next node to the queue for processing
            def add_to_queue(next_node):
                if next_node:
                    # No need to check processed_nodes here; the check at the start of the loop handles it.
                    queue.append(next_node)

            # Append outgoing edges for the current node
            if isinstance(node, ActionNode):
                lines.append(f"    --next--> {node.next if node.next else '<exit>'}")
                add_to_queue(node.next)
            elif isinstance(node, ConditionNode):
                lines.append(
                    f"    --true--> {node.true_next if node.true_next else '<exit>'}"
                )
                lines.append(
                    f"    --false--> {node.false_next if node.false_next else '<exit>'}"
                )
                add_to_queue(node.true_next)
                add_to_queue(node.false_next)
            elif isinstance(node, BreakNode):
                # Assuming target in BreakNode should ideally not be None
                lines.append(
                    f"    --target--> {node.target.label() if node.target else '<unspecified_target>'}"
                )
                add_to_queue(node.target)
            elif isinstance(node, ReturnNode):
                if node.value_source:
                    lines.append(f"    (returns: {node.value_source})")
                else:
                    lines.append(f"    (returns: None)")
                # ReturnNode has no outgoing edges to add to the queue for graph traversal display
            else:
                # Fallback for any other Node subclasses not explicitly handled
                lines.append(
                    f"    (Unknown node type: {type(node).__name__}, no defined edges in __repr__)"
                )

        return "\n".join(lines)
