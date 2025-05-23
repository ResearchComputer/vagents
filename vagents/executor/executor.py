from .graph import Graph
from vagents.core import InRequest, OutResponse
import importlib
import itertools


def has_next(iterator_name: str, context: dict):
    """
    Checks if the iterator in the context (specified by iterator_name) has more elements.
    If it does, it updates the iterator in the context to a new one that will
    yield the peeked element first, and then returns True.
    Otherwise, returns False.
    """
    iterator = context.get(iterator_name)
    if iterator is None:
        # This case should ideally not happen if the graph is built correctly
        raise NameError(f"Iterator '{iterator_name}' not found in context.")

    try:
        first_element = next(iterator)
        # Put the first element back by creating a new chained iterator
        context[iterator_name] = itertools.chain([first_element], iterator)
        return True
    except StopIteration:
        return False
    except TypeError:  # Handle cases where context[iterator_name] is not an iterator
        return False


class GraphExecutor:
    """Runs a graph until there is no next node."""

    def __init__(
        self, graph: Graph, module_instance=None, global_context=None
    ):  # Added module_instance
        self.ctx = {"__builtins__": __builtins__, "has_next": has_next}
        if global_context:
            self.ctx.update(global_context)

        self.module_instance = module_instance  # Store module_instance

        if self.module_instance:
            # Add attributes of module_instance to the shared context
            for attr_name, attr_value in vars(self.module_instance).items():
                if attr_name not in self.ctx:  # Avoid overwriting existing keys
                    self.ctx[attr_name] = attr_value
            # Also include the module's globals (imports, classes) into context
            module_name = self.module_instance.__class__.__module__
            try:
                mod = importlib.import_module(module_name)
                for name, val in vars(mod).items():
                    if name not in self.ctx:
                        self.ctx[name] = val
            except ImportError:
                pass

        self.graph = graph.optimize()

    def run(self, requests: list[InRequest]) -> list[OutResponse]:
        responses = []
        for request in requests:
            # Create a new context for each request to avoid interference
            current_ctx = self.ctx.copy()
            current_ctx[
                "request"
            ] = request  # Make the request available in the context
            current_ctx["query"] = request  # Alias to match parameter name in graph execution

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

                current_ctx['__execution_context__'] = current_ctx # Add context reference

                executed_node_result = node.execute(current_ctx)

                del current_ctx['__execution_context__'] # Remove context reference

                # Restore 'self' in context to its previous state
                if had_original_ctx_self:
                    current_ctx["self"] = original_ctx_self_val
                else:
                    # If 'self' was not in current_ctx before we set it, remove it.
                    if "self" in current_ctx:
                        del current_ctx["self"]

                node = executed_node_result

            # Assuming the result of the graph execution is stored in current_ctx['__return__']
            # Append the return value to responses
            responses.append(current_ctx.get("__return__"))

        # Return all collected responses
        return responses
