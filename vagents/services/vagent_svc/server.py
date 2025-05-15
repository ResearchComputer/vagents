import importlib
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from vagents.core import InRequest
from vagents.utils import logger
from .server_handler import handle_response_request
from .protocols import (
    ModuleRegistrationRequest,
)
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
        self.router.post("/v1/execute")(self.execute_requests)
        # endpoint for streaming responses
        self.router.get("/v1/stream_responses")(self.stream_responses)
        # /v1/responses for legacy handler
        self.router.post("/v1/responses")(self.response_handler)

        # /api/* are for internal use
        self.router.post("/api/job")(self.dispatch_job)
        self.router.post("/api/module")(self.register_module)
        self.router.post("/api/mcp_server")(self.register_mcp_server)

    # register a module for execution
    async def register_module(self, req: ModuleRegistrationRequest):
        module_spec = req.module
        # parse module spec, format 'module.path:ClassName' or 'module.path.ClassName'
        if ":" in module_spec:
            mod_path, class_name = module_spec.split(":", 1)
        elif "." in module_spec:
            parts = module_spec.split(".")
            mod_path, class_name = ".".join(parts[:-1]), parts[-1]
        else:
            raise HTTPException(status_code=400, detail="Invalid module spec")
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, class_name)
            config = VModuleConfig()
            module_instance = cls(config)
            # compile execution graph from forward method
            source = inspect.getsource(module_instance.forward)
            graph = GraphBuilder().build(source)
            # store and register in scheduler
            self.modules[module_spec] = (graph, module_instance)
            self.scheduler.register_module(module_spec, graph, module_instance)
            return JSONResponse(content={"status": "module registered"}, status_code=200)
        except Exception as e:
            logger.error(f"Error registering module {module_spec}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # execute list of requests synchronously
    async def execute_requests(self, reqs: List[InRequest]):
        out_resps = []
        async for resp in self.scheduler.dispatch(reqs):
            out_resps.append(resp)
        return JSONResponse(content=[r.dict() for r in out_resps])

    # stream responses as they complete
    async def stream_responses(self):
        async def event_stream():
            async for resp in self.scheduler.responses():
                yield json.dumps(resp.dict()) + "\n"
        return StreamingResponse(event_stream(), media_type="application/json")

    async def response_handler(self, req: InRequest):
        # auto-register module if needed
        if req.module not in self.modules:
            await self.register_module(ModuleRegistrationRequest(module=req.module, force=False))
        # schedule the request
        self.scheduler.add_request(req)
        # wait for this request's response
        if req.stream:
            async def gen():
                async for resp in self.scheduler.responses():
                    if resp.id == req.id:
                        yield json.dumps(resp.dict()) + "\n"
                        break
            return StreamingResponse(gen(), media_type="application/json")
        else:
            async for resp in self.scheduler.responses():
                if resp.id == req.id:
                    return JSONResponse(content=resp.dict())

def start_server(port: int = 8000):
    import uvicorn
    app = FastAPI()
    router = APIRouter()
    VServer(router, port=port)
    app.include_router(router)
    uvicorn.run("vagents.services.vagent_svc.server:app", host="0.0.0.0", port=port)
