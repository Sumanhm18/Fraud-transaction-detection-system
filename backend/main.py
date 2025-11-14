"""
FinSentinel AI - Main FastAPI Application
Autonomous Financial Intelligence & Trust System
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import make_asgi_app
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import get_settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.api.v1.router import api_router
from app.services.orchestrator import AgentOrchestrator
from app.services.websocket_manager import WebSocketManager

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global instances
orchestrator = AgentOrchestrator()
websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    settings = get_settings()
    logger.info("Starting FinSentinel AI", version="1.0.0", env=settings.env)
    
    try:
        # Initialize databases
        await init_db()
        await init_redis()
        
        # Initialize agent orchestrator
        await orchestrator.initialize()
        
        logger.info("FinSentinel AI startup complete")
        yield
        
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    finally:
        # Cleanup
        await orchestrator.shutdown()
        logger.info("FinSentinel AI shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    # Initialize Sentry for error tracking
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration(auto_enabling=True)],
            traces_sample_rate=0.1,
            environment=settings.env,
        )
    
    # Create FastAPI app
    app = FastAPI(
        title="FinSentinel AI",
        description="Autonomous Financial Intelligence & Trust System",
        version="1.0.0",
        docs_url="/docs" if settings.env == "development" else None,
        redoc_url="/redoc" if settings.env == "development" else None,
        lifespan=lifespan,
    )
    
    # Add middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.websocket_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Add Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    return app


# Create app instance
app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FinSentinel AI",
        "version": "1.0.0",
        "agents": await orchestrator.get_agent_status() if orchestrator else {}
    }


@app.websocket("/ws/transactions")
async def websocket_transactions(websocket: WebSocket):
    """WebSocket endpoint for real-time transaction updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.info("WebSocket message received", data=data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        websocket_manager.disconnect(websocket)


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for real-time fraud alerts"""
    await websocket_manager.connect(websocket, channel="alerts")
    try:
        while True:
            data = await websocket.receive_text()
            logger.info("Alert WebSocket message", data=data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, channel="alerts")
    except Exception as e:
        logger.error("Alert WebSocket error", error=str(e))
        websocket_manager.disconnect(websocket, channel="alerts")


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.env == "development",
        log_level=settings.log_level.lower(),
    )