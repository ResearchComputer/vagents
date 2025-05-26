import importlib
import itertools

from .graph import Graph
from .node import ReturnNode

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
        self.base_ctx = {"__builtins__": __builtins__, "has_next": has_next} # Renamed to base_ctx
        if global_context:
            self.base_ctx.update(global_context)

        self.module_instance = module_instance

        if self.module_instance:
            for attr_name, attr_value in vars(self.module_instance).items():
                if attr_name not in self.base_ctx:
                    self.base_ctx[attr_name] = attr_value
            
            # Make the module instance available as 'self' in the context
            self.base_ctx['self'] = self.module_instance

            module_name = self.module_instance.__class__.__module__
            try:
                mod = importlib.import_module(module_name)
                for name, val in vars(mod).items():
                    if name not in self.base_ctx:
                        self.base_ctx[name] = val
            except ImportError:
                pass

        self.graph = graph.optimize()

    async def run(self, inputs: list[any]): # Changed to async def
        """Execute the graph with the given inputs, yielding results for streaming."""
        # For true streaming, we process one input at a time and yield from it.
        # If multiple inputs are meant to be processed sequentially for a single stream, 
        # this logic would need adjustment. Assuming one input produces one stream of results.
        for i, inp in enumerate(inputs):
            current_run_ctx = self.base_ctx.copy()
            current_run_ctx.update({
                "__execution_context__": {},
                "__yielded_values_stream__": [] # This will be used by YieldNode
            })
            current_run_ctx['query'] = inp

            current_node = self.graph.entry
            while current_node:
                if isinstance(current_node, ReturnNode):
                    return_value = eval(current_node.code, current_run_ctx, current_run_ctx) if current_node.code else None
                    # If YieldNodes were used, their values are already yielded directly by current_node.execute
                    # The final return_value of the graph might be an OutResponse or a simple value.
                    # If it's an OutResponse, it could be the final piece of a stream or the whole non-streamed response.
                    if return_value is not None:
                        yield return_value # Yield the final return value
                    break
                
                # Node execution itself might yield multiple items if it's a YieldNode or similar
                # We need to handle if current_node.execute becomes an async generator
                if hasattr(current_node, 'is_generator') and current_node.is_generator:
                    async for yielded_item_from_node in current_node.execute(current_run_ctx):
                        yield yielded_item_from_node
                    # After an async generator node, we need to get the next node to continue graph execution.
                    # This assumes the generator node itself returns the next node after it's exhausted.
                    # This part is tricky and depends on how YieldNode.execute is structured.
                    # For now, let's assume execute() sets up the stream and returns next node or None.
                    # The change to YieldNode will handle the actual yielding.
                    current_node = current_node.next # This might need to be set by the node itself if it yields
                else:
                    # For ActionNode and ConditionNode, execute will be async if they handle await
                    next_node_or_val = await current_node.execute(current_run_ctx) # Await here
                    if isinstance(next_node_or_val, tuple) and next_node_or_val[0] == "YIELD":
                        # This is a temporary way to handle yields from non-YieldNodes if necessary
                        yield next_node_or_val[1]
                        current_node = next_node_or_val[2]
                    else:
                        current_node = next_node_or_val

            # If the graph finished without a ReturnNode but had yields (e.g. from a loop with YieldNodes)
            # those would have been yielded already by the node.execute calls.
            # The __yielded_values_stream__ in context was for the old YieldNode model.
            # With direct yielding from nodes, it might not be the primary mechanism.
