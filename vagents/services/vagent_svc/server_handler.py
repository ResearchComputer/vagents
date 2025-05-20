import json
import traceback
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from vagents.utils import logger
from vagents.core import InRequest, OutResponse


async def handle_response_request(modules, req: InRequest) -> OutResponse:
    if req.module not in modules:
        logger.error(f"Module {req.module} not registered")
        return HTTPException(status_code=400, detail="Module not registered")
    module = modules[req.module]
    # Use the async method from LLM instead of directly calling the instance
    if req.stream:

        async def stream_results():
            try:
                async for chunk in module.forward(query=req):
                    yield json.dumps(chunk.to_dict()) + "\n"
            except Exception as e:
                logger.error(f"Error in streaming response: {e}")
                yield JSONResponse(content={"error": str(e)}, status_code=500)

        return stream_results()
    else:
        try:
            response = await module.forward(query=req)
        except Exception as e:
            traceback.print_exc()
            return JSONResponse(content={"error": str(e)}, status_code=500)
        finally:
            await module.cleanup(req.id)
    return response
