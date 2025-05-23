from vagents.core import Message
from typing import List, Union, Dict

class Session:
    def __init__(self, session_id: str)-> None:
        self.session_id = session_id
        self.history: List[Message] = []

    def append(self, message: Union[Dict, List[Message], Message])-> None:
        if isinstance(message, Message):
            self.history.append(message)
        elif isinstance(message, List):
            for sub_item in message:
                self.append(sub_item)
        elif isinstance(message, Dict):
            self.history.append(Message.model_validate(message))
        else:
            raise TypeError(f"Unsupported type: {type(message)}")
    
    def clear(self)-> None:
        self.history = []

    def __repr__(self)-> str:
        repr = f"----- {self.session_id} -----\n"
        for message in self.history:
            repr += f"[{message.role}]: {message.content}\n"
        repr += "---------------------\n"
        return repr