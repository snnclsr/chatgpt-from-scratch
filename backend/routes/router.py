# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
# from typing import List, Dict, Any
# import logging


# from ml.factory import ModelFactory
# from ml.config import DEFAULT_GENERATION_PARAMS

# logger = logging.getLogger(__name__)

# router = APIRouter()


# @router.get("/models", response_model=List[Dict[str, Any]])
# async def list_models():
#     """List all available models and their status"""
#     return ModelFactory.get_available_models()


# # @router.post("/models/{model_id}/load")
# # async def load_model(model_id: str):
# #     """Explicitly load a model into memory"""
# #     try:
# #         await ModelFactory.get_model(model_id)
# #         return {"status": "success", "message": f"Model {model_id} loaded successfully"}
# #     except Exception as e:
# #         logger.error(f"Error loading model {model_id}: {str(e)}")
# #         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/models/{model_id}/unload")
# async def unload_model(model_id: str):
#     """Unload a model from memory"""
#     try:
#         await ModelFactory.unload_model(model_id)
#         return {
#             "status": "success",
#             "message": f"Model {model_id} unloaded successfully",
#         }
#     except Exception as e:
#         logger.error(f"Error unloading model {model_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.websocket("/ws/{model_id}")
# async def websocket_endpoint(websocket: WebSocket, model_id: str):
#     await websocket.accept()
#     logger.info(f"New WebSocket connection for model: {model_id}")

#     try:
#         model = await ModelFactory.get_model(model_id)

#         while True:
#             data = await websocket.receive_json()
#             prompt = data.get("prompt")
#             params = {**DEFAULT_GENERATION_PARAMS, **(data.get("params", {}))}

#             if not prompt:
#                 await websocket.send_json({"error": "No prompt provided"})
#                 continue

#             try:
#                 async for token in model.generate_stream(prompt, params):
#                     await websocket.send_json({"token": token, "finished": False})

#                 await websocket.send_json({"finished": True})

#             except Exception as e:
#                 logger.error(f"Generation error: {str(e)}")
#                 await websocket.send_json({"error": str(e)})

#     except WebSocketDisconnect:
#         logger.info(f"Client disconnected from model: {model_id}")
#     except Exception as e:
#         logger.error(f"WebSocket error: {str(e)}")
#         await websocket.close(code=1011, reason=str(e))
