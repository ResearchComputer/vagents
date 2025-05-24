import json
import inspect
import uvicorn
import importlib
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, FastAPI, HTTPException, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
import dill

from vagents.executor import VScheduler, GraphBuilder
from vagents.core import InRequest, VModuleConfig
from vagents.utils import logger

from .server_handler import handle_response_request
from .protocols import (
    ModuleRegistrationRequest,
)
from .args import ServerArgs

app: FastAPI = FastAPI()

# Assuming 'modules' is your module registry, adjust its definition if necessary
# For example: modules: Dict[str, Dict[str, Any]] = {}
# This might be globally defined or part of a class/application context
modules: Dict[str, Dict[str, Any]] = {}

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
        self.router.post("/api/modules")(self.register_module)
        
    async def register_module(self, request: Request):
        form = await request.form()
        module_content = form.get('module_content')
        force = form.get('force', 'false').lower() == 'true'
        mcp_configs_json = form.get('mcp_configs')

        try:
            if module_content is None:
                logger.error("Module content is missing.")
                return JSONResponse(
                    {"error": "Module content is missing."},
                    status_code=400
                )

            pickled_module_bytes = await (module_content).read()
            if not pickled_module_bytes:
                logger.error("Module content is empty during registration.")
                return JSONResponse(
                    {"error": "Module content is empty."},
                    status_code=400
                )

            class_obj = dill.loads(pickled_module_bytes)
            module_name = f"{class_obj.__module__}:{class_obj.__name__}"

            parsed_mcp_configs: Optional[List[Dict[str, Any]]] = None
            if mcp_configs_json:
                try:
                    parsed_mcp_configs = json.loads(mcp_configs_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON for mcp_configs for module {module_name}: {e}")
                    return JSONResponse(
                        {"error": f"Invalid JSON format for mcp_configs: {str(e)}"},
                        status_code=400
                    )

            # Store the module and its configurations
            if module_name in modules and not force:
                logger.warning(f"Module {module_name} already registered. Use force=True to overwrite.")
                return JSONResponse(
                    {"error": f"Module {module_name} already registered. Use force=True to overwrite."},
                    status_code=409
                )

            self.modules[module_name] = {
                "class": class_obj,
                "mcp_configs": parsed_mcp_configs,
            }
            logger.info(f"Module {module_name} registered successfully. Force: {force}, MCP Configs: {parsed_mcp_configs}")
            return JSONResponse(
                {"message": f"Module {module_name} registered successfully."},
                status_code=200
            )

        except dill.UnpicklingError as e:
            logger.error(f"Deserialization error for module: {e}", exc_info=True)
            return JSONResponse(
                {"error": f"Module deserialization error: {str(e)}"},
                status_code=400
            )
        except Exception as e:
            logger.error(f"Failed to register module: {e}", exc_info=True)
            return JSONResponse(
                {"error": f"Internal server error during module registration: {str(e)}"},
                status_code=500
            )
    
    async def response_handler(self, req: InRequest):
        return await handle_response_request(self.modules, req)

def start_server(args: ServerArgs) -> None:
    router: APIRouter = APIRouter()
    VServer(router, port=args.port)
    app.include_router(router)
    uvicorn.run(
        "vagents.services.vagent_svc.server:app",
        host="0.0.0.0",
        port=args.port
    )
