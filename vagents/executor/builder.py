import ast
import inspect
import textwrap
from .graph import Graph
from .node import Node, ActionNode, ConditionNode, BreakNode, ReturnNode, YieldNode


class GraphBuilder:
    def __init__(self):
        self.lines: list[str] = []
        self.indent_map: dict[int, int] = {}
        self.loop_stack: list[tuple[Node, Node]] = []

    def build(self, source: str):
        src = textwrap.dedent(source)
        self.lines = src.splitlines()
        self.indent_map = {
            i + 1: len(line) - len(line.lstrip()) for i, line in enumerate(self.lines)
        }
        tree = ast.parse(src)
        if len(tree.body) == 1 and isinstance(
            tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            stmts = tree.body[0].body
        else:
            stmts = tree.body
        flat = sorted(((stmt.lineno, stmt) for stmt in stmts), key=lambda x: x[0])
        entry = self._build_from_flat(
            flat, next_node=ReturnNode(None)
        )  # Ensure a default return for the graph
        return Graph(entry)

    def _build_from_flat(self, flat: list[tuple[int, ast.AST]], next_node):
        if not flat:
            return next_node
        # Stack entries: (indent, exit_node, last_node_in_block)
        stack: list[tuple[int, Node | None, Node | None]] = [(0, next_node, None)]
        head_of_sequence: Node | None = None  # To store the first node of the sequence.

        for lineno, stmt in flat:
            indent = self.indent_map.get(lineno, 0)
            # Close any blocks we have left
            while indent < stack[-1][0]:
                _, exit_node_for_popped_block, last_node_of_popped_block = stack.pop()
                if last_node_of_popped_block and hasattr(
                    last_node_of_popped_block, "next"
                ):
                    if (
                        not isinstance(
                            last_node_of_popped_block, (ReturnNode, BreakNode)
                        )
                        and last_node_of_popped_block.next is None
                    ):
                        last_node_of_popped_block.next = exit_node_for_popped_block

            if indent > stack[-1][0]:
                stack.append((indent, stack[-1][1], None))

            # node_default_next is the general exit target of the current block on stack
            # This is what a statement should go to if it's the last in its sequence or falls through.
            node_default_next = stack[-1][1]
            node = self._make_node(stmt, node_default_next)

            if head_of_sequence is None:
                head_of_sequence = node

            # Link from the previous node in the current block to the current node `node`
            _block_indent, block_exit_target_for_linking, last_node_in_block = stack[-1]
            if last_node_in_block:
                # Relink all fall-through paths of the previous logical statement block (last_node_in_block)
                # that were pointing to the general block exit (block_exit_target_for_linking),
                # to instead point to the current node (`node`).
                self._relink_node_successors(
                    last_node_in_block, block_exit_target_for_linking, node
                )
                # Nodes like ReturnNode don't have a 'next' to link from.

            stack[-1] = (_block_indent, block_exit_target_for_linking, node)

        # Close any remaining open blocks
        while len(stack) > 1:
            _, exit_node_for_popped_block, last_node_of_popped_block = stack.pop()
            if last_node_of_popped_block and hasattr(last_node_of_popped_block, "next"):
                if (
                    not isinstance(last_node_of_popped_block, (ReturnNode, BreakNode))
                    and last_node_of_popped_block.next is None
                ):
                    last_node_of_popped_block.next = exit_node_for_popped_block

        # Finalize .next for the very last node of the base block if it's not set
        # and it's a type that should have a .next (e.g. ActionNode)
        _final_indent, final_exit_node, final_last_node = stack[0]
        if (
            final_last_node
            and hasattr(final_last_node, "next")
            and final_last_node.next is None
        ):
            if isinstance(
                final_last_node, ActionNode
            ):  # Only ActionNodes typically fall through like this
                final_last_node.next = final_exit_node

        return head_of_sequence

    def _relink_node_successors(
        self, current_node, old_target, new_target, visited=None
    ):
        if visited is None:
            visited = set()

        if not current_node or current_node in visited:
            return
        visited.add(current_node)

        # Nodes that terminate flow or have specific jump targets handled by their creation logic
        if isinstance(
            current_node, (ReturnNode, BreakNode)
        ):  # Add ContinueNode if it exists and behaves similarly
            return

        if isinstance(current_node, ConditionNode):
            # If a branch pointed directly to old_target (e.g., empty branch), update it.
            if current_node.true_next == old_target:
                current_node.true_next = new_target
            # Else, recurse if not None (it might be already pointing to something else)
            elif current_node.true_next is not None:
                self._relink_node_successors(
                    current_node.true_next, old_target, new_target, visited.copy()
                )  # Use copy of visited for independent branch traversal

            if current_node.false_next == old_target:
                current_node.false_next = new_target
            elif current_node.false_next is not None:
                self._relink_node_successors(
                    current_node.false_next, old_target, new_target, visited.copy()
                )  # Use copy of visited

        elif hasattr(current_node, "next"):  # ActionNode, etc.
            if current_node.next == old_target:
                current_node.next = new_target
            # If current_node.next is not old_target and not None, it means this node is part of
            # an internal sequence. We should still recurse on its .next, because that sequence
            # might *eventually* lead to old_target.
            elif current_node.next is not None:
                self._relink_node_successors(
                    current_node.next, old_target, new_target, visited
                )
        # If a node has no 'next' attribute and is not a ConditionNode/Return/Break,
        # it's implicitly done, or it's an error/unhandled type.

    def _make_node(
        self, stmt, next_node
    ):  # next_node is the default fallthrough for this stmt
        # Simple sequential statements
        if isinstance(
            stmt,
            (
                ast.Assign,
                ast.AugAssign,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Pass,
            ),
        ):
            return ActionNode(ast.unparse(stmt), next_node)

        # Yield statement
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield):
            # If stmt.value.value is None, it's a bare 'yield'
            yield_expr_src = (
                ast.unparse(stmt.value.value) if stmt.value.value else "None"
            )
            return YieldNode(yield_expr_src, next_node)

        # If / else
        if isinstance(stmt, ast.If):
            cond = ConditionNode(ast.unparse(stmt.test))
            # The 'next_node' is where to go after the if/else construct.
            false_first = self._build_from_flat(
                sorted((s.lineno, s) for s in stmt.orelse or []),
                next_node,  # After else body, go to common next_node
            )
            true_first = self._build_from_flat(
                sorted((s.lineno, s) for s in stmt.body),
                next_node,  # After true body, go to common next_node
            )
            cond.true_next, cond.false_next = true_first, false_first
            return cond

        # While loop
        if isinstance(stmt, ast.While):
            cond = ConditionNode(ast.unparse(stmt.test))
            # next_node is where to go when the loop condition is false (loop exit)
            self.loop_stack.append((cond, next_node))

            body_first = self._build_from_flat(
                sorted((s.lineno, s) for s in stmt.body),
                cond,  # After body, go back to condition
            )

            self.loop_stack.pop()

            cond.true_next, cond.false_next = body_first, next_node
            return cond

        # For loop
        if isinstance(stmt, ast.For):
            iter_src = ast.unparse(stmt.iter)
            iter_var = f"__iter_{stmt.lineno}"

            # Conceptual condition node for the loop (re-entry point for continue)
            # The actual iteration logic (next() and StopIteration) is embedded.
            # `next_node` is the exit point if the loop terminates normally.
            loop_condition_surrogate = ConditionNode(
                f"has_next('{iter_var}', __execution_context__)"  # Pass iter_var as string and context
            )

            self.loop_stack.append((loop_condition_surrogate, next_node))

            init_node = ActionNode(
                f"__execution_context__['{iter_var}'] = iter({iter_src})",
                loop_condition_surrogate,
            )

            assign_target_code = f"{ast.unparse(stmt.target)} = next(__execution_context__['{iter_var}'])"
            # This assign_node conceptually sits after a successful check by loop_condition_surrogate
            assign_node = ActionNode(
                assign_target_code, None
            )  # Its .next will be body_first

            body_first = self._build_from_flat(
                sorted((s.lineno, s) for s in stmt.body),
                loop_condition_surrogate,  # After body, go back to loop condition check
            )
            assign_node.next = body_first

            # If loop_condition_surrogate is "true" (has_next), then assign and do body
            loop_condition_surrogate.true_next = assign_node
            # If loop_condition_surrogate is "false" (StopIteration), then exit to next_node
            loop_condition_surrogate.false_next = next_node

            # TODO: Handle 'orelse' for 'for' loops if present.
            # It would execute if the loop finishes normally (not via break).
            # The false_next would go to orelse_first, and orelse_first's next is next_node.

            self.loop_stack.pop()
            return init_node  # Entry to the for loop construct

        # Return
        if isinstance(stmt, ast.Return):
            value_src = ast.unparse(stmt.value) if stmt.value else None
            return ReturnNode(value_src)

        # Break / continue
        if isinstance(stmt, ast.Break):
            if not self.loop_stack:
                # This should ideally raise a SyntaxError or create an ErrorNode
                return ActionNode(
                    f"# ERROR: break outside loop: {ast.unparse(stmt)}", next_node
                )
            # Break jumps to the exit node of the innermost loop
            return BreakNode(self.loop_stack[-1][1])

        if isinstance(stmt, ast.Continue):
            if not self.loop_stack:
                # This should ideally raise a SyntaxError or create an ErrorNode
                return ActionNode(
                    f"# ERROR: continue outside loop: {ast.unparse(stmt)}", next_node
                )
            # Continue jumps to the head/condition of the innermost loop
            # Assuming BreakNode is a generic jump node for now.
            # Ideally, this would be a ContinueNode(self.loop_stack[-1][0])
            return BreakNode(self.loop_stack[-1][0])

        # Fallback
        return ActionNode(ast.unparse(stmt), next_node)


def compile_to_graph(func):
    if callable(func):
        src: str = inspect.getsource(func)
    builder: GraphBuilder = GraphBuilder()
    return builder.build(src)
