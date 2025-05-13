from .graph import Graph
from vagents.core import InRequest, OutResponse


class GraphExecutor:
    """Runs a graph until there is no next node."""

    def __init__(
        self, graph: Graph, module_instance=None, global_context=None
    ):  # Added module_instance
        self.ctx = {"__builtins__": __builtins__}
        if global_context:
            self.ctx.update(global_context)

        self.module_instance = module_instance  # Store module_instance

        if self.module_instance:
            # Add attributes of module_instance to the shared context
            for attr_name, attr_value in vars(self.module_instance).items():
                if attr_name not in self.ctx:  # Avoid overwriting existing keys
                    self.ctx[attr_name] = attr_value

        self.graph = graph.optimize()

    def run(self, requests: list[InRequest]) -> list[OutResponse]:
        responses = []
        for request in requests:
            # Create a new context for each request to avoid interference
            current_ctx = self.ctx.copy()
            current_ctx[
                "request"
            ] = request  # Make the request available in the context

            node = self.graph.entry
            while node is not None:
                # Preserve original 'self' from context if it exists
                original_ctx_self_val = current_ctx.get("self")
                had_original_ctx_self = "self" in current_ctx

                # Set 'self' in the execution context
                if self.module_instance:
                    current_ctx[
                        "self"
                    ] = self.module_instance  # 'self' is the module instance
                else:
                    # Fallback to original behavior if no module_instance is provided
                    current_ctx["self"] = node

                executed_node_result = node.execute(current_ctx)

                # Restore 'self' in context to its previous state
                if had_original_ctx_self:
                    current_ctx["self"] = original_ctx_self_val
                else:
                    # If 'self' was not in current_ctx before we set it, remove it.
                    if "self" in current_ctx:
                        del current_ctx["self"]

                node = executed_node_result

            # Assuming the result of the graph execution is stored in current_ctx['__return__']
