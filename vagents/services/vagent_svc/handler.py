import dill
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any, AsyncGenerator

from vagents.utils import logger
from vagents.core import InRequest, OutResponse
from vagents.executor import compile_to_graph, GraphExecutor, Graph, VScheduler # Added VScheduler

async def register_module_handler(
        existing_modules: Dict[str, Any],
        scheduler: VScheduler,
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
            logger.error(
                "Module content is empty during registration."
            )
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

        # Instantiate the module
        actual_module_instance = class_obj(mcp_configs=parsed_mcp_configs) if parsed_mcp_configs else class_obj()

        compiled_graph: Graph | None = compile_to_graph(actual_module_instance.forward) if hasattr(actual_module_instance, 'forward') else None

        executor_for_dict: GraphExecutor | None = GraphExecutor(
            compiled_graph, module_instance=actual_module_instance
        ) if compiled_graph else None
        
        # Register with the scheduler if graph-based
        if compiled_graph:
            scheduler.register_module(
                module_name=module_name,
                compiled_graph=compiled_graph,
                module_instance=actual_module_instance # Pass the same instance
            )
            logger.info(f"Module {module_name} registered with VScheduler.")
        else:
            logger.info(f"Module {module_name} not graph-based, not registered with VScheduler.")

        return module_name, {
            "class": class_obj,
            "mcp_configs": parsed_mcp_configs,
            "compiled_graph": compiled_graph,
            "executor": executor_for_dict, # Executor for the dict
            "module_instance": actual_module_instance # Store the instance
        }

    except dill.UnpicklingError as e:
        logger.error(
            f"Deserialization error for module: {e}", 
            exc_info=True
        )
        raise ValueError(
            f"Module deserialization error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Failed to register module: {e}", exc_info=True)
        raise ValueError(f"Failed to register module: {str(e)}")

async def handle_response(
    available_modules: Dict[str, Any], # Changed type
    scheduler: VScheduler,             # Added scheduler
    req: InRequest
) -> JSONResponse | StreamingResponse:
    module_name: str = req.module
    if module_name not in available_modules:
        logger.error(f"Module {module_name} not found.")
        return JSONResponse(
            {"error": f"Module {module_name} not found."},
            status_code=404
        )
    module_info = available_modules[module_name]
    
    # Check if the module is registered and thus schedulable
    # A module is typically registered if it has a compiled_graph.
    # scheduler._executors is an internal detail, checking compiled_graph is safer.
    is_schedulable = module_info.get("compiled_graph") is not None and req.module in scheduler._executors

    if is_schedulable:
        logger.info(f"Using VScheduler for module {module_name} for request {req.id}.")
        try:
            response_task = scheduler.add_request(req)
            final_out_response: OutResponse = await response_task
            
            if req.stream:
                logger.debug(f"Streaming mode on for scheduled request {req.id}...")
                
                async def stream_wrapper_scheduled() -> AsyncGenerator[str, Any]:
                    if not hasattr(final_out_response, 'output') or not isinstance(final_out_response.output, AsyncGenerator):
                        logger.warning(f"Scheduled response for streaming request {req.id} output is not an async generator. Type: {type(final_out_response.output)}")
                        if final_out_response.output is not None:
                             yield json.dumps({"type": "data", "content": str(final_out_response.output)}) + "\\n"
                        return

                    async for item in final_out_response.output:
                        # print(f"Streaming item from scheduled: {item}") # For debugging
                        if isinstance(item, str):
                            yield json.dumps({"type": "data", "content": item}) + "\n"
                        elif isinstance(item, dict):
                            yield json.dumps(item) + "\n"
                        elif isinstance(item, OutResponse):
                            if item.output and isinstance(item.output, str):
                                yield json.dumps({"type": "data", "content": item.output}) + "\n"
                        else:
                            logger.warning(f"Unsupported item type in scheduled stream for {req.id}: {type(item)}")
                return StreamingResponse(stream_wrapper_scheduled(), media_type="application/x-ndjson")
            
            else: # Non-streaming for scheduled request
                # final_out_response should be a complete OutResponse object.
                # Its .output field should contain the aggregated string.
                response_dict = final_out_response.model_dump(exclude_none=True)
                if not isinstance(response_dict.get("output"), str):
                    logger.warning(f"Non-streaming scheduled response {req.id} output is not a string. Type: {type(response_dict.get('output'))}. Converting to string.")
                    response_dict["output"] = str(response_dict.get("output", ""))
                logger.info(f"Non-streaming scheduled response for {req.id} constructed from OutResponse.")
                return JSONResponse(content=response_dict)

        except Exception as e:
            logger.error(f"Error processing request by VScheduler for module {module_name} (req_id: {req.id}): {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error in VScheduler for module {module_name}: {str(e)}")
    
    else: # Fallback: Module not schedulable, use original direct execution logic
        logger.info(f"Module {module_name} (req_id: {req.id}) not using VScheduler, using direct execution logic.")
        module_class = module_info["class"]
        mcp_configs = module_info["mcp_configs"]
        # The executor here is from module_info, which might be None if not graph-based
        executor = module_info.get('executor') 
        
        try:
            # module_instance = module_info.get("module_instance") # Get pre-created instance
            # if not module_instance: # Fallback if not found, though it should be there
            # logger.warning(f"Module instance not found in module_info for {module_name}, creating new one.")
            if hasattr(module_class, '__init__') and 'mcp_configs' in module_class.__init__.__code__.co_varnames:
                module_instance = module_class(mcp_configs=mcp_configs)
            else:
                module_instance = module_class()
        except Exception as e:
            logger.error(f"Error instantiating module {module_name} for direct execution (req_id: {req.id}): {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error instantiating module {module_name}: {str(e)}")
        
        if not hasattr(module_instance, 'forward'):
            raise HTTPException(status_code=501, detail=f"Module {module_name} does not have a forward method.")
        
        try:
            if executor: # This is the GraphExecutor from module_info
                logger.info(f"Using GraphExecutor directly for module {module_name} (req_id: {req.id}).")
                # executor.run will be changed to an async generator
                response_generator = executor.run([req]) 
            else:
                logger.info(f"Using direct module.forward() for module {module_name} (req_id: {req.id}).")
                response_generator = module_instance.forward(req)
            
            if req.stream:
                logger.debug(f"streaming mode on for direct execution (req_id: {req.id})...")
                
                async def stream_wrapper() -> AsyncGenerator[str, Any]:
                    # Now response_generator is always an async generator
                    async for item in response_generator:
                        print(f"Streaming item (direct): {item}")
                        if isinstance(item, str):
                            yield json.dumps({"type": "data", "content": item}) + "\\n"
                        elif isinstance(item, dict):
                            yield json.dumps(item) + "\\n"
                        elif isinstance(item, OutResponse):
                            if item.output and isinstance(item.output, str):
                                yield json.dumps({"type": "data", "content": item.output}) + "\\n"
                        else:
                            logger.warning(f"Unsupported item type in stream for {req.id}: {type(item)}")
                return StreamingResponse(stream_wrapper(), media_type="application/x-ndjson")
            
            else: # Non-streaming for direct execution
                all_data_chunks: list[str] = []
                final_out_response: Optional[OutResponse] = None
                
                # Now response_generator is always an async generator
                async for item in response_generator:
                    if isinstance(item, str):
                        all_data_chunks.append(item)
                    elif isinstance(item, OutResponse):
                        if item.output and isinstance(item.output, str):
                            all_data_chunks.append(item.output)
                        final_out_response = item 
                        if not executor: 
                            break 
                    else:
                        logger.warning(f"Unsupported item type in non-streaming response for {req.id}: {type(item)}")

                combined_response_content: str = "".join(all_data_chunks)

                if final_out_response:
                    response_dict = final_out_response.model_dump(exclude_none=True)
                    response_dict["output"] = combined_response_content
                    logger.info(f"Non-streaming response for {req.id} (direct) constructed from OutResponse.")
                    return JSONResponse(content=response_dict)
                else:
                    logger.error(f"No OutResponse found for non-streaming response for {req.id} (direct). Using fallback.")

                    return JSONResponse(content={
                        "output": combined_response_content,
                        "id": req.id,
                        "input": req.input,
                        "module": req.module,
                        "session_history": [],
                    })
        except Exception as e:
            logger.error(f"Error processing request by module {module_name} (direct) (req_id: {req.id}): {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing request by module {module_name}: {str(e)}")
