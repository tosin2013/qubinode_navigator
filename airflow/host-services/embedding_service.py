#!/usr/bin/env python3
"""
Qubinode Embedding Service
ADR-0050: Hybrid Host-Container Architecture

This service runs on the host (not in container) to provide vector embeddings
for the RAG system. Running on host allows:
- GPU acceleration if available
- Shared model cache across tools
- Reduced container image size

Port: 8891
"""

import os
import logging
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
MODEL_CACHE_DIR = os.environ.get("TRANSFORMERS_CACHE", "/opt/qubinode/models")

# Global model instance
model = None


class EmbedRequest(BaseModel):
    """Request model for embedding generation."""

    texts: List[str]
    normalize: bool = True


class EmbedResponse(BaseModel):
    """Response model for embedding generation."""

    embeddings: List[List[float]]
    model: str
    dimensions: int


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    model: str
    dimensions: int
    device: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown."""
    global model
    logger.info(f"Loading embedding model: {MODEL_NAME}")

    try:
        from sentence_transformers import SentenceTransformer

        # Set cache directory
        os.environ["TRANSFORMERS_CACHE"] = MODEL_CACHE_DIR
        os.environ["HF_HOME"] = MODEL_CACHE_DIR

        # Load model (will use GPU if available via CUDA)
        model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_CACHE_DIR)

        device = str(model.device)
        dimensions = model.get_sentence_embedding_dimension()

        logger.info(f"Model loaded successfully on {device}")
        logger.info(f"Embedding dimensions: {dimensions}")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down embedding service")
    model = None


app = FastAPI(
    title="Qubinode Embedding Service",
    description="Vector embedding service for RAG (ADR-0050)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    """
    Generate embeddings for a list of texts.

    Args:
        request: EmbedRequest with texts and normalization option

    Returns:
        EmbedResponse with embeddings, model name, and dimensions
    """
    global model

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    if len(request.texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per request")

    try:
        logger.info(f"Generating embeddings for {len(request.texts)} texts")

        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            show_progress_bar=False,
        )

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            model=MODEL_NAME,
            dimensions=model.get_sentence_embedding_dimension(),
        )

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    global model

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return HealthResponse(
        status="healthy",
        model=MODEL_NAME,
        dimensions=model.get_sentence_embedding_dimension(),
        device=str(model.device),
    )


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Qubinode Embedding Service",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "endpoints": {
            "embed": "POST /embed - Generate embeddings",
            "health": "GET /health - Health check",
        },
    }


if __name__ == "__main__":
    port = int(os.environ.get("EMBEDDING_SERVICE_PORT", 8891))
    host = os.environ.get("EMBEDDING_SERVICE_HOST", "0.0.0.0")

    logger.info(f"Starting embedding service on {host}:{port}")

    uvicorn.run(app, host=host, port=port, log_level="info")
