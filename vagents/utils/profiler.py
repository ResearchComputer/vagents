from timeit import default_timer as timer
from .logger import logger

profiler_data = {}
# Track counts of event names per session
event_counters = {}


class Profiler:
    def __init__(self, session_id=None, name=None):
        """
        Initialize the Profiler.

        Args:
            session_id: An identifier for the profiling session
            name: A name for the operation being profiled
        """
        self.session_id = session_id
        self.name = name
        self.start_time = None
        self.end_time = None
        self.execution_time = None
        self.unique_name = None

    def __enter__(self):
        """Start the timer when entering the context."""
        self.start_time = timer()

        # Store start time in global_profiler_storage
        if self.session_id is not None and self.name is not None:
            if self.session_id not in profiler_data:
                profiler_data[self.session_id] = {}
                event_counters[self.session_id] = {}

            # Initialize counter for this event name if not exists
            if self.name not in event_counters[self.session_id]:
                event_counters[self.session_id][self.name] = 0

            # Increment counter for this event name
            event_counters[self.session_id][self.name] += 1
            counter = event_counters[self.session_id][self.name]

            # Create unique name with counter
            self.unique_name = f"{self.name}_{counter}"

            if self.unique_name not in profiler_data[self.session_id]:
                profiler_data[self.session_id][self.unique_name] = {}

            profiler_data[self.session_id][self.unique_name]["begin"] = self.start_time

        logger.debug(
            f"Starting profiler for {self.name} (session: {self.session_id}, instance: {event_counters[self.session_id][self.name]})"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Calculate execution time when exiting the context."""
        self.end_time = timer()
        self.execution_time = self.end_time - self.start_time

        # Store end time in global_profiler_storage
        if self.session_id is not None and self.name is not None:
            if (
                self.session_id in profiler_data
                and self.unique_name in profiler_data[self.session_id]
            ):
                profiler_data[self.session_id][self.unique_name]["end"] = self.end_time

        counter = event_counters[self.session_id][self.name]
        logger.debug(
            f"Profiler result for {self.name} (session: {self.session_id}, instance: {counter}): {self.execution_time:.4f} seconds"
        )
        return False  # Re-raise any exceptions

    def get_execution_time(self):
        """Return the execution time in seconds."""
        return self.execution_time