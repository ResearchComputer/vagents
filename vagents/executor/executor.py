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

    def run(self, inputs: list[any]):
        """Execute the graph with the given inputs."""
        results = []
        for i, inp in enumerate(inputs):
            # Create a new context for each run, inheriting from base_ctx
            current_run_ctx = self.base_ctx.copy()
            current_run_ctx.update({
                "__execution_context__": {},
                # "__module_instance__": self.module_instance, # Already in base_ctx if module_instance exists
                "__yielded_values_stream__": [] 
            })
            
            # Make the InRequest object available as 'query' in the current run's context
            # This assumes the compiled graph expects the input InRequest to be named 'query',
            # which is typical if it's from a method like `forward(self, query: InRequest)`.
            current_run_ctx['query'] = inp

            # Optionally, if you still want InRequest attributes as top-level vars (be cautious of name clashes):
            # if hasattr(inp, '__dict__'):
            #     for key, value in inp.__dict__.items():
            #         if key not in current_run_ctx: # Avoid overwriting existing important context vars
            #             current_run_ctx[key] = value

            current_node = self.graph.entry
            while current_node:
                if isinstance(current_node, ReturnNode):
                    return_value = eval(current_node.code, current_run_ctx, current_run_ctx) if current_node.code else None
                    if current_run_ctx["__yielded_values_stream__"]:
                        results.append(current_run_ctx["__yielded_values_stream__"])
                    else:
                        results.append(return_value)
                    break
                
                current_node = current_node.execute(current_run_ctx)
            
            if not current_node and current_run_ctx["__yielded_values_stream__"] and not results:
                 results.append(current_run_ctx["__yielded_values_stream__"])
                 
        print(f"results: {results}")
        return results[0] if len(results) == 1 else results
