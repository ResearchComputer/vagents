from vagents.core import LLM

class LMManager:
    def __init__(self):
        self.models = {}
    
    def add_model(self, llm: LLM):
        self.models[llm.model_name] = llm
    
    async def call(self, model_name: str, *args, **kwargs):
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found.")
        res = await self.models[model_name](*args, **kwargs)
        res = await res.__anext__()
        return res