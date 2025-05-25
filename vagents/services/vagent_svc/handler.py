import dill
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any, AsyncGenerator

from vagents.utils import logger
from vagents.core import InRequest, OutResponse

async def register_module_handler(
        existing_modules:List,
        request: Request
    ) -> None:
    
    form = await request.form()
    module_content = form.get('module_content')
    force: bool = form.get('force', 'false').lower() == 'true'
    mcp_configs_json = form.get('mcp_configs')
    
    try:
        if module_content is None:
            logger.error("Module content is missing.")
            raise ValueError("Module content is missing.")
            
        pickled_module_bytes: bytes = await (module_content).read()
        if not pickled_module_bytes:
            logger.error("Module content is empty during registration.")
            raise ValueError("Module content is empty.")

        class_obj = dill.loads(pickled_module_bytes)
        module_name: str = f"{class_obj.__module__}:{class_obj.__name__}"

        parsed_mcp_configs: Optional[List[Dict[str, Any]]] = None
        if mcp_configs_json:
            try:
                parsed_mcp_configs = json.loads(mcp_configs_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON for mcp_configs for module {module_name}: {e}")
                raise ValueError(f"Invalid JSON format for mcp_configs: {str(e)}")

        if module_name in existing_modules and not force:
            logger.warning(f"Module {module_name} already registered. Use force=True to overwrite.")
            raise ValueError(f"Module {module_name} already registered. Use force=True to overwrite.")

        return module_name, {
            "class": class_obj,
            "mcp_configs": parsed_mcp_configs,
        }
        
    except dill.UnpicklingError as e:
        logger.error(f"Deserialization error for module: {e}", exc_info=True)
        raise ValueError(f"Module deserialization error: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to register module: {e}", exc_info=True)
        raise ValueError(f"Failed to register module: {str(e)}")

async def handle_response(available_modules, req: InRequest) -> JSONResponse | StreamingResponse:
    module_name: str = req.module
    if module_name not in available_modules:
        logger.error(f"Module {module_name} not found.")
        return JSONResponse(
            {"error": f"Module {module_name} not found."},
            status_code=404
        )
    module_info = available_modules[module_name]
    module_class = module_info["class"]
    mcp_configs = module_info["mcp_configs"]
    
    try:
        if hasattr(module_class, '__init__') and 'mcp_configs' in module_class.__init__.__code__.co_varnames:
                module_instance = module_class(mcp_configs=mcp_configs)
        else:
                module_instance = module_class()
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
