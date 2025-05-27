import uvicorn

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vagents.utils import logger
from vagents.core import InRequest
from vagents.executor import VScheduler, compile_to_graph, GraphExecutor

from .args import ServerArgs
from .handler import register_module_handler, handle_response

app: FastAPI = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VServer:
    def __init__(self, router: APIRouter, port: int) -> None:
        self.router = router
        self.port = port
        self.modules = {}

        self.scheduler = VScheduler() # Scheduler is initialized here
        self.router.get("/health", tags=["health"])(lambda: {"status": "ok"})

        # /v1/* are public, user-facing APIs
        self.router.post("/v1/responses")(self.response_handler)
        # /api/* are for internal use
        self.router.post("/api/modules")(self.register_module)

    async def register_module(self, request: Request):
        try:
            # Pass self.scheduler to register_module_handler
            module_name, registered_module = await register_module_handler(self.modules, self.scheduler, request)

        except ValueError as e:
            logger.error(f"Error registering module: {e}", exc_info=True)
            return JSONResponse(
                {"error": str(e)},
                status_code=400
            )
        if registered_module is None:
            logger.error("Failed to register module.")
            return JSONResponse(
                {"error": f"Module {module_name} already registered. Use force=True to overwrite."},
                status_code=409
            )
        self.modules[module_name] = registered_module
        print(f"Module {module_name} registered successfully with mcp_configs: {registered_module['mcp_configs']}")

    async def response_handler(self, req: InRequest):
        # Pass self.scheduler to handle_response
        return await handle_response(self.modules, self.scheduler, req)

def start_server(args: ServerArgs) -> None:
    router: APIRouter = APIRouter()
    VServer(router, port=args.port)
    app.include_router(router)
    uvicorn.run(
        "vagents.services.vagent_svc.server:app",
        host="0.0.0.0",
        port=args.port
    )
