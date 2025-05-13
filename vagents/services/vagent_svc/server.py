import importlib
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from vagents.core import InputRequest
from vagents.utils import logger

from .server_handler import handle_response_request
from .server_protocols import (
    DispatchJobRequest,
    ModuleRegistrationRequest,
    MCPServerRegistrationRequest,
)


class Controller:
    def __init__(self, router: APIRouter, port: int) -> None:
        self.router = router
        self.port = port
        # module is given as filepath:classname
        self.modules = {}
        # /v1/* are public, user-facing APIs
        self.router.get("/health", tags=["health"])(lambda: {"status": "ok"})
        self.router.post("/v1/responses")(self.response_handler)

        # /api/* are for internal use
        self.router.post("/api/job")(self.dispatch_job)
        self.router.post("/api/module")(self.register_module)
        self.router.post("/api/mcp_server")(self.register_mcp_server)

    async def register_module(self, req: ModuleRegistrationRequest):
        logger.debug(f"Register module: {req}")
        if req.module in self.modules and not req.force:
            return HTTPException(status_code=400, detail="Module already registered")
        try:
            module_name, class_name = req.module.split(":")
            module_def = importlib.import_module(module_name)
            module_def = getattr(module_def, class_name)
            self.modules[req.module] = module_def()
            return JSONResponse(
                content={
                    "message": "Module registered successfully",
                    "module": req.module,
                }
            )
        except Exception as e:
            return HTTPException(
                status_code=400, detail=f"Failed to register module: {e}"
            )

    async def register_mcp_server(self, req: MCPServerRegistrationRequest):
        logger.debug(f"Register module: {req}")

    async def response_handler(self, req: InputRequest):
        if req.stream:
            stream_generator = await handle_response_request(self.modules, req)
            res = StreamingResponse(stream_generator, media_type="text/event-stream")
        else:
            res = await handle_response_request(self.modules, req)
        return res

    async def dispatch_job(self, req: DispatchJobRequest):
        # code, output = await self.jd.dispatch(req.session_id, req.job)
        code, output = 0, "ok"
        return {
            "return_code": code,
            "output": output,
        }


def start_server(port: int = 8000):
    import uvicorn

    app = FastAPI()
    router = APIRouter()
    Controller(router, port=port)
    app.include_router(router)
    uvicorn.run(app, host="0.0.0.0", port=port)
