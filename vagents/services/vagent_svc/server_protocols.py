from pydantic import BaseModel


class WorkerRegistrationRequest(BaseModel):
    name: str
    image: str


class DispatchJobRequest(BaseModel):
    session_id: str
    job: dict


class ModuleRegistrationRequest(BaseModel):
    module: str
    force: bool


class MCPServerRegistrationRequest(BaseModel):
    ...
