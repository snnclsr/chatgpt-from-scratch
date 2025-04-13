import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models
from .database import engine

from .routes.base_routes import router as base_router
from .routes.chat_routes import router as chat_router
from .routes.websockets.chat import router as ws_chat_router
from .routes.websockets.vision import router as ws_vision_router

from .ml.factory import ModelFactory
from .ml.config import MODEL_CONFIGS
from .utils.image_utils import UPLOADS_DIR, ensure_upload_dir

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Ensure the uploads directory exists
ensure_upload_dir()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register all models from config
    for model_id, config in MODEL_CONFIGS.items():
        logger.info(f"Registering model: {model_id}")
        await ModelFactory.get_model(model_id)

    yield

    # Clean up
    for model_id in MODEL_CONFIGS.keys():
        await ModelFactory.unload_model(model_id)


app = FastAPI(title="AI Chat System", lifespan=lifespan)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(base_router)
app.include_router(chat_router)
app.include_router(ws_chat_router)
app.include_router(ws_vision_router)

# Mount the uploads directory for static file access
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
