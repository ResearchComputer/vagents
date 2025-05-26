import time
import heapq

class Module:
    def __init__(self, name: str, base_time_per_node: float):
        self.name = name
        self.base_time_per_node = base_time_per_node

    def get_execution_time(self, num_nodes: int) -> float:
        """Calculates execution time based on the number of nodes."""
        return self.base_time_per_node * num_nodes

    def __repr__(self):
        return f"Module(name='{self.name}', base_time_per_node={self.base_time_per_node})"

class UserRequest:
    def __init__(self, user_id: str, module_name: str, num_nodes: int, request_time: float):
        self.user_id = user_id
        self.module_name = module_name
        self.num_nodes = num_nodes
        self.request_time = request_time
        self.start_time: float | None = None
        self.finish_time: float | None = None
        self.actual_execution_time: float | None = None


    def __repr__(self):
        return (f"UserRequest(user_id='{self.user_id}', module_name='{self.module_name}', "
                f"num_nodes={self.num_nodes}, request_time={self.request_time:.2f})")

class Simulator:
    EVENT_TYPE_REQUEST = "REQUEST"
    EVENT_TYPE_MODULE_FINISH = "MODULE_FINISH"

    def __init__(self):
        self.modules: dict[str, Module] = {}
        self.event_queue = []  # A min-heap: (event_time, event_type, event_data)
        self.current_time: float = 0.0
        self.completed_requests: list[UserRequest] = []
        self.request_counter = 0 # To maintain order for events at the same time

    def add_module(self, module: Module):
        """Adds a module to the simulator."""
        if module.name in self.modules:
            print(f"Warning: Module {module.name} already exists. Overwriting.")
        self.modules[module.name] = module
        print(f"Simulator: Added {module}")

    def add_user_request(self, user_id: str, module_name: str, num_nodes: int, request_time: float | None = None):
        """Adds a user request to the event queue."""
        if module_name not in self.modules:
            print(f"Error: Module {module_name} not found. Request ignored.")
            return

        req_time = request_time if request_time is not None else self.current_time
        if req_time < self.current_time:
            print(f"Warning: Request time {req_time} is in the past. Using current time {self.current_time}.")
            req_time = self.current_time
        
        self.request_counter += 1
        request = UserRequest(user_id, module_name, num_nodes, req_time)
        heapq.heappush(self.event_queue, (req_time, self.request_counter, self.EVENT_TYPE_REQUEST, request))
        print(f"Simulator: Queued {request} at time {req_time:.2f}")

    def _process_request_event(self, request: UserRequest):
        """Processes a user request event."""
        module = self.modules.get(request.module_name)
        if not module: # Should have been checked in add_user_request, but good for safety
            print(f"Error: Module {request.module_name} for {request.user_id} disappeared! Skipping.")
            return

        execution_time = module.get_execution_time(request.num_nodes)
        request.start_time = self.current_time # Assuming immediate start for simplicity now
        request.finish_time = self.current_time + execution_time
        request.actual_execution_time = execution_time
        
        self.request_counter += 1
        heapq.heappush(self.event_queue, (request.finish_time, self.request_counter, self.EVENT_TYPE_MODULE_FINISH, request))
        print(f"Time {self.current_time:.2f}: User '{request.user_id}' started module '{request.module_name}' (nodes: {request.num_nodes}). Finishes at {request.finish_time:.2f}.")

    def _process_module_finish_event(self, request: UserRequest):
        """Processes a module finish event."""
        self.completed_requests.append(request)
        print(f"Time {self.current_time:.2f}: User '{request.user_id}' finished module '{request.module_name}' (nodes: {request.num_nodes}). Duration: {request.actual_execution_time:.2f}.")


    def run(self):
        """Runs the simulation until the event queue is empty."""
        print(f"Simulator: Starting run at time {self.current_time:.2f}. Events in queue: {len(self.event_queue)}")
        while self.event_queue:
            event_time, _, event_type, event_data = heapq.heappop(self.event_queue)

            if event_time < self.current_time:
                # This can happen if multiple events are scheduled for the same time
                # or due to floating point inaccuracies. We process them at current_time.
                pass
            else:
                self.current_time = event_time

            if event_type == self.EVENT_TYPE_REQUEST:
                request: UserRequest = event_data
                self._process_request_event(request)
            elif event_type == self.EVENT_TYPE_MODULE_FINISH:
                request: UserRequest = event_data
                self._process_module_finish_event(request)
            else:
                print(f"Error: Unknown event type {event_type} at time {self.current_time:.2f}")

        print(f"Simulator: Run finished at time {self.current_time:.2f}. Total completed requests: {len(self.completed_requests)}")
        return self.completed_requests

def example_usage():
    print("\n--- Simulator Example ---")
    sim = Simulator()

    # Define modules
    module_a = Module(name="DataProcessing", base_time_per_node=0.5)
    module_b = Module(name="MachineLearningModel", base_time_per_node=2.0)
    module_c = Module(name="ReportGenerator", base_time_per_node=0.1)

    sim.add_module(module_a)
    sim.add_module(module_b)
    sim.add_module(module_c)

    # Add user requests (user_id, module_name, num_nodes, request_time)
    # Requests can be added with specific submission times
    sim.add_user_request(user_id="User1", module_name="DataProcessing", num_nodes=10, request_time=0.0)
    sim.add_user_request(user_id="User2", module_name="MachineLearningModel", num_nodes=5, request_time=1.0)
    sim.add_user_request(user_id="User1", module_name="ReportGenerator", num_nodes=100, request_time=2.0)
    sim.add_user_request(user_id="User3", module_name="DataProcessing", num_nodes=20, request_time=0.5)
    sim.add_user_request(user_id="User2", module_name="DataProcessing", num_nodes=5, request_time=6.0) # After first DP for User1 finishes

    # Run the simulation
    completed = sim.run()

    print("\n--- Simulation Results ---")
    if not completed:
        print("No requests were completed.")
    else:
        # Sort by finish time for clearer output
        completed.sort(key=lambda r: r.finish_time if r.finish_time is not None else float('inf'))
        for req in completed:
            print(f"User: {req.user_id}, Module: {req.module_name}, Nodes: {req.num_nodes}, "
                  f"Requested: {req.request_time:.2f}, Started: {req.start_time:.2f}, Finished: {req.finish_time:.2f}, "
                  f"Duration: {req.actual_execution_time:.2f}")
    print("-------------------------\n")

if __name__ == "__main__":
    example_usage()
