import importlib
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from vagents.core import InRequest
from vagents.utils import logger
from .server_handler import handle_response_request
from .protocols import (
    ModuleRegistrationRequest,
)
from .args import ServerArgs
from typing import List
import inspect
import json
from vagents.executor.scheduler import VScheduler
from vagents.executor.builder import GraphBuilder
from vagents.core.module import VModuleConfig

class VServer:
    def __init__(self, router: APIRouter, port: int) -> None:
        self.router = router
        self.port = port
        # module is given as filepath:classname
        self.modules = {}
        # integrate scheduler
        self.scheduler = VScheduler()
        # /v1/* are public, user-facing APIs
        self.router.get("/health", tags=["health"])(lambda: {"status": "ok"})
        # endpoint for synchronous execution
        
        self.router.post("/v1/responses")(self.response_handler)

        # /api/* are for internal use
        self.router.post("/api/job")(self.dispatch_job)
        self.router.post("/api/module")(self.register_module)
        self.router.post("/api/mcp_server")(self.register_mcp_server)

    # register a module for execution
    async def register_module(self, req: ModuleRegistrationRequest) -> JSONResponse:
        module_spec: str = req.module
        
    async def response_handler(self, req: InRequest):
        pass

def start_server(args: ServerArgs) -> None:
    import uvicorn
    app: FastAPI = FastAPI()
    router: APIRouter = APIRouter()
    
    VServer(router, port=args.port)
    app.include_router(router)
    
    uvicorn.run(
        "vagents.services.vagent_svc.server:app",
        host="0.0.0.0",
        port=args.port
    )
