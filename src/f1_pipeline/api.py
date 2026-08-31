import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from f1_pipeline.logging_config import configure_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))  # ← here, once
    logger.info("F1 pipeline starting up")
    yield
    logger.info("F1 pipeline shutting down")

app = FastAPI(lifespan=lifespan)