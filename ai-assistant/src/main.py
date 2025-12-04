#!/usr/bin/env python3
"""
Qubinode AI Assistant Main Application
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture

This module provides the main entry point for the AI assistant service,
implementing a REST API for AI inference using llama.cpp and Granite-4.0-Micro.
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from enhanced_ai_service import create_enhanced_ai_service
from config_manager import ConfigManager
from health_monitor import HealthMonitor
from rag_ingestion_api import router as rag_router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Global services
config_manager = None
ai_service = None
health_monitor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global config_manager, ai_service, health_monitor

    # Startup
    try:
        logger.info("Starting Qubinode AI Assistant...")

        # Initialize configuration manager
        config_manager = ConfigManager()
        await config_manager.load_config()

        # Initialize enhanced AI service
        ai_service = create_enhanced_ai_service(config_manager.config)
        await ai_service.initialize()

        # Initialize health monitor with AI service reference
        health_monitor = HealthMonitor(ai_service)

        logger.info("Qubinode AI Assistant started successfully")

    except Exception as e:
        logger.error(f"Failed to start AI Assistant: {e}")
        sys.exit(1)

    yield

    # Shutdown
    logger.info("Shutting down Qubinode AI Assistant...")

    if ai_service:
        await ai_service.cleanup()

    logger.info("Shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Qubinode AI Assistant",
    description="CPU-based AI deployment assistant for infrastructure automation",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rag_router)


class ChatRequest(BaseModel):
    """Request model for chat interactions."""

    message: str
    context: dict = {}
    max_tokens: int = 512
    temperature: float = 0.7


class ChatResponse(BaseModel):
    """Response model for chat interactions."""

    response: str
    context: dict = {}
    metadata: dict = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Service not ready")

    health_status = await health_monitor.get_health_status()

    if health_status["status"] == "healthy":
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Qubinode AI Assistant",
        "version": "1.1.0",
        "status": "running",
        "features": {
            "rag": "Document retrieval for context-aware responses",
            "lineage": "Real-time infrastructure state from Marquez/OpenLineage",
        },
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "diagnostics": "/diagnostics",
            "diagnostics_tools": "/diagnostics/tools",
            "specific_tool": "/diagnostics/tool/{tool_name}",
            "lineage": "/lineage",
            "lineage_job": "/lineage/job/{job_name}",
            "models": "/models",
            "docs": "/docs",
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint for AI interactions."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        response = await ai_service.process_message(
            message=request.message,
            context=request.context,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return ChatResponse(
            response=response["text"],
            context=response.get("context", {}),
            metadata=response.get("metadata", {}),
        )

    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/diagnostics")
async def run_diagnostics(request: dict):
    """Run system diagnostics and provide AI-powered analysis."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        diagnostics_result = await ai_service.run_diagnostics(request)
        return diagnostics_result

    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics error: {str(e)}")


@app.get("/diagnostics/tools")
async def list_diagnostic_tools():
    """List all available diagnostic tools."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        tools = ai_service.get_available_diagnostic_tools()
        return {
            "available_tools": tools,
            "total_tools": len(tools),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Tools listing error: {e}")
        raise HTTPException(status_code=500, detail=f"Tools listing error: {str(e)}")


@app.post("/diagnostics/tool/{tool_name}")
async def run_specific_diagnostic_tool(tool_name: str, request: dict = None):
    """Run a specific diagnostic tool by name."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        request_data = request or {}
        result = await ai_service.run_specific_diagnostic_tool(tool_name, **request_data)
        return result

    except Exception as e:
        logger.error(f"Specific tool error: {e}")
        raise HTTPException(status_code=500, detail=f"Tool execution error: {str(e)}")


@app.get("/model/info")
async def get_model_info():
    """Get current model information."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        model_info = ai_service.get_model_info()
        return {"model_info": model_info, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Model info error: {e}")
        raise HTTPException(status_code=500, detail=f"Model info error: {str(e)}")


@app.get("/model/hardware")
async def get_hardware_info():
    """Get hardware capabilities and recommendations."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        hardware_info = ai_service.get_hardware_info()
        return {"hardware_info": hardware_info, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Hardware info error: {e}")
        raise HTTPException(status_code=500, detail=f"Hardware info error: {str(e)}")


@app.get("/config")
async def get_config():
    """Get current configuration (sanitized)."""
    if not config_manager:
        raise HTTPException(status_code=503, detail="Config service not available")

    return config_manager.get_sanitized_config()


# =============================================================================
# Lineage Endpoints (Marquez/OpenLineage Integration)
# =============================================================================


@app.get("/lineage")
async def get_lineage_summary():
    """Get infrastructure lineage summary from Marquez.

    Returns current state of DAG runs, failures, and deployment history.
    This data is also used to enhance AI responses with real-time context.
    """
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        summary = await ai_service.get_lineage_summary()
        return {"lineage": summary, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Lineage summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Lineage error: {str(e)}")


@app.get("/lineage/job/{job_name}")
async def get_job_lineage(job_name: str):
    """Get detailed lineage for a specific job/DAG.

    Args:
        job_name: The name of the job/DAG (e.g., 'freeipa_deployment', 'dns_management')
    """
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        job_info = await ai_service.get_job_lineage(job_name)
        if job_info is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_name}' not found")
        return {"job": job_info, "timestamp": time.time()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job lineage error for {job_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Lineage error: {str(e)}")


def main():
    """Main entry point."""
    # Get configuration from environment
    host = os.getenv("AI_HOST", "0.0.0.0")
    port = int(os.getenv("AI_PORT", "8080"))
    log_level = os.getenv("AI_LOG_LEVEL", "info")

    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,  # Disable reload in production
    )


if __name__ == "__main__":
    main()
