import json
import traceback
from typing import Any, AsyncGenerator
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from vagents.utils import logger
from vagents.core import InRequest, OutResponse


def _format_chunk_for_sse(chunk: Any) -> str:
    """Helper to format various chunk types into a JSON string for SSE."""
    if hasattr(chunk, "model_dump_json"):  # Pydantic v2
        return chunk.model_dump_json() + "\\n"
    if hasattr(chunk, "json"):  # Pydantic v1
        return chunk.json() + "\\n"
    if hasattr(chunk, "to_dict"):  # Custom to_dict method
        return json.dumps(chunk.to_dict()) + "\\n"
    if isinstance(chunk, dict):
        return json.dumps(chunk) + "\\n"
    # Default for other types, like str
    return json.dumps({"content": str(chunk)}) + "\\n"


async def handle_response_request(modules: dict, req: InRequest) -> OutResponse:
    if req.module not in modules:
        logger.error(f"Module {req.module} not registered")
        raise HTTPException(status_code=404, detail=f"Module {req.module} not registered")

    module_info = modules[req.module]
    module_class = module_info.get("class")
    mcp_configs_for_instance = module_info.get("mcp_configs")
    # Optionally, retrieve other stored info like default_model if you added it
    # default_model_for_instance = module_info.get("default_model")

    if not module_class:
        logger.error(f"Class not found for module {req.module} in registry.")
        raise HTTPException(status_code=500, detail=f"Configuration error: Class not found for module {req.module}.")

    module_instance = None

    try:
        # Instantiate the module, passing stored mcp_configs and other relevant args
        # Adjust the instantiation based on what your module constructors expect.
        # This is a general example; DeepResearch might have specific needs.
        # If default_model is also crucial and stored:
        # module_instance = module_class(default_model=default_model_for_instance, mcp_configs=mcp_configs_for_instance)
        # If only mcp_configs are passed from registration:
        if hasattr(module_class, "__init__"):
            import inspect
            sig = inspect.signature(module_class.__init__)
            init_params = {}
            if "mcp_configs" in sig.parameters:
                init_params["mcp_configs"] = mcp_configs_for_instance
            # Add other parameters like 'default_model' if they are part of registration and __init__
            # For example, if you stored 'default_model' during registration:
            # if "default_model" in sig.parameters and module_info.get("default_model") is not None:
            #     init_params["default_model"] = module_info.get("default_model")
            
            module_instance = module_class(**init_params)
        else:
            module_instance = module_class() # Fallback if no explicit __init__ or simple one

    except Exception as e:
        logger.error(f"Failed to instantiate module {req.module} with mcp_configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to instantiate module {req.module}: {str(e)}")

    try:
        if req.stream:
            response_obj = await module_instance.forward(query=req)

            async def stream_generator_wrapper():
                try:
                    if isinstance(response_obj.output, AsyncGenerator):
                        async for chunk in response_obj.output:
                            yield _format_chunk_for_sse(chunk)
                    elif response_obj.output is not None:
                        # Stream the single output if module doesn't provide an async generator
                        yield _format_chunk_for_sse(response_obj.output)
                    # If response_obj.output is None, the stream will be empty.
                except Exception as e_stream_gen:
                    logger.error(f"Error during stream data generation for {req.module}: {e_stream_gen}", exc_info=True)
                    yield json.dumps({"error": f"Streaming data error in {req.module}: {str(e_stream_gen)}"}) + "\\n"
                finally:
                    if module_instance:
                        try:
                            await module_instance.cleanup(req.id)
                        except Exception as e_cleanup:
                            logger.error(f"Error during cleanup (after stream gen) for {req.module}, session {req.id}: {e_cleanup}", exc_info=True)
            
            return StreamingResponse(stream_generator_wrapper(), media_type="text/event-stream")
        else: # Not streaming
            response = await module_instance.forward(query=req)
            return response # FastAPI will serialize the OutResponse Pydantic model

    except Exception as e_forward:
        import traceback
        traceback.print_exc()
        logger.error(f"Error processing request in module {req.module}: {e_forward}", exc_info=True)
        # Ensure cleanup is attempted if forward fails after instantiation
        raise HTTPException(status_code=500, detail=f"Error in module {req.module}: {str(e_forward)}")
    finally:
        # For non-streaming cases, or if req.stream was true but forward() failed before returning StreamingResponse
        if not req.stream and module_instance: # Cleanup for non-streaming path
            try:
                await module_instance.cleanup(req.id)
            except Exception as e_cleanup:
                logger.error(f"Error during cleanup for {req.module}, session {req.id}: {e_cleanup}", exc_info=True)
