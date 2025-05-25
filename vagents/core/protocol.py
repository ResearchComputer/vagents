from enum import Enum
from uuid import uuid4
from dataclasses import dataclass
from timeit import default_timer as timer
from pydantic import BaseModel, Field, ConfigDict
from typing import Union, List, Dict, Any, Optional
from typing import AsyncGenerator

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool-call"
    AGENT = "agent"
    TOOL_RESPONSE = "tool-response"

    @classmethod
    def roles(cls):
        return [r.value for r in cls]

    @classmethod
    def from_str(cls, role_str):
        if role_str not in cls.roles():
            role_str = "user"
        return cls(role_str)

    def __repr__(self):
        return super().__repr__()


class Message(BaseModel):
    role: MessageRole
    content: str
    def to_dict(self):
        return {
            "role": self.role.value,
            "content": self.content
        }

class ActionOutputStatus(str, Enum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    CANCELLED = "cancelled"
    AGENT_CONTEXT_LIMIT = "agent context limit"


class ActionOutput(BaseModel):
    status: ActionOutputStatus = ActionOutputStatus.NORMAL
    content: Union[str, dict] = None


@dataclass
class Metrics:
    def __init__(self):
        self.running_events = {}
        self.events = []
        self.event_counters = {}

    def record_start(self, event_name):
        if event_name in self.running_events:
            # Get the counter for this event name
            count = self.event_counters.get(event_name, 0)
            # Create a new event name with the counter
            new_event_name = f"{event_name}_{count}"
            # Increment the counter for next time
            self.event_counters[event_name] = count + 1
            # Get the current event data
            event_data = self.running_events[event_name].copy()
            # Set end time to now
            event_data["end"] = timer()
            # Add the name to the event data
            event_data["name"] = new_event_name
            # Push the completed event to events list
            self.events.append(event_data)
            # Start a new event with the original name
            self.running_events[event_name] = {"start": timer(), "end": None}
        else:
            # This is the first time we're seeing this event
            self.running_events[event_name] = {"start": timer(), "end": None}
            # Initialize the counter for this event name
            self.event_counters[event_name] = 0

    def record_end(self, event_name):
        if event_name in self.running_events:
            self.running_events[event_name]["end"] = timer()
            # Add the completed event to the events list
            event_data = self.running_events[event_name].copy()
            event_data["name"] = event_name
            self.events.append(event_data)
            # Remove from running events
            del self.running_events[event_name]

    def clear(self):
        self.running_events = {}
        self.events = []
        self.event_counters = {}


class InRequest(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    module: str
    input: Union[str, List["Message"], Dict[str, Any]]
    stream: bool = False
    additional: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OutResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    input: Union[str, List["Message"], Dict[str, Any]]
    module: str
    session: Optional[List["Message"]] = None
    metrics: Optional[Metrics] = None
    events: Optional[Dict[str, Any]] = None
    output: Optional[Union[str, List["Message"], AsyncGenerator]] = None
