import json
import dill
import uvicorn
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, FastAPI, HTTPException, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from vagents.executor import VScheduler
from vagents.core import InRequest, VModuleConfig, OutResponse
from vagents.utils import logger

from .args import ServerArgs
from typing import AsyncGenerator, Any

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
        force: bool = form.get('force', 'false').lower() == 'true'
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
            if module_name in self.modules and not force:
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
        module_name = req.module
        if module_name not in self.modules:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_name} not found."
            )

        module_info = self.modules[module_name]
        module_class = module_info["class"]
        mcp_configs = module_info["mcp_configs"]

        try:
            if hasattr(module_class, '__init__') and 'mcp_configs' in module_class.__init__.__code__.co_varnames:
                module_instance = module_class(mcp_configs=mcp_configs)
            else:
                module_instance = module_class() # Or however your modules are instantiated
        except Exception as e:
            logger.error(f"Error instantiating module {module_name}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error instantiating module {module_name}: {str(e)}")

        if not hasattr(module_instance, 'forward'):
            raise HTTPException(status_code=501, detail=f"Module {module_name} does not have a forward method.")

        try:
            response_generator = module_instance.forward(req)

            if req.stream:
                async def stream_wrapper() -> AsyncGenerator[str, Any]:
                    async for item in response_generator:
                        if isinstance(item, str):
                            yield json.dumps({"type": "data", "content": item}) + "\n\n"
                        elif isinstance(item, OutResponse):
                            if item.output and isinstance(item.output, str):
                                yield json.dumps({"type": "data", "content": item.output}) + "\n\n"
                            break # OutResponse is considered terminal for the stream
                        else:
                            logger.warning(f"Unsupported item type in stream for {req.id}: {type(item)}")
                return StreamingResponse(stream_wrapper(), media_type="application/x-ndjson")
            else:
                # Non-streaming: Collect all parts
                all_data_chunks: list[str] = []
                final_out_response: Optional[OutResponse] = None
                
                async for item in response_generator:
                    if isinstance(item, str):
                        all_data_chunks.append(item)
                    elif isinstance(item, OutResponse):
                        if item.output and isinstance(item.output, str):
                            all_data_chunks.append(item.output)
                        final_out_response = item
                        break # OutResponse is considered terminal
                    else:
                        logger.warning(f"Unsupported item type in non-streaming response for {req.id}: {type(item)}")

                combined_response_content: str = "".join(all_data_chunks)

                if final_out_response:
                    response_dict = final_out_response.model_dump(exclude_none=True)
                    response_dict["output"] = combined_response_content
                    logger.info(f"Non-streaming response for {req.id} constructed from OutResponse.")
                    return JSONResponse(content=response_dict)
                else:
                    logger.error(f"No OutResponse found for non-streaming response for {req.id}. Using fallback.")
                    
                    return JSONResponse(content={
                        "output": combined_response_content,
                        "id": req.id,
                        "input": req.input, # Ensure req.input is serializable or handle appropriately
                        "module": req.module,
                        "session_history": [], # Basic fallback
                    })

        except Exception as e:
            logger.error(f"Error processing request by module {module_name}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing request by module {module_name}: {str(e)}")

def start_server(args: ServerArgs) -> None:
    router: APIRouter = APIRouter()
    VServer(router, port=args.port)
    app.include_router(router)
    uvicorn.run(
        "vagents.services.vagent_svc.server:app",
        host="0.0.0.0",
        port=args.port
    )
