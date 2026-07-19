# backend/app/main.py
from contextlib import asynccontextmanager
import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

from app.core.config import settings
from app.core.database import db_manager, get_db, get_redis
from app.api.v1 import auth, workspaces, documents, chat

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.LOG_LEVEL == "INFO" else structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing application startup...")
    await db_manager.connect()
    
    yield
    
    # Shutdown actions
    logger.info("Initializing application shutdown...")
    await db_manager.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-tenant Enterprise RAG Knowledge Base and Search Engine Backend API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logger middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        "request_processed",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    return response

# Auto-instrument Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Healthcheck route
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    db_ok = False
    redis_ok = False
    
    # Check MongoDB
    try:
        if db_manager.mongo_client:
            await db_manager.db.command("ping")
            db_ok = True
    except Exception as e:
        logger.error("healthcheck_mongo_failed", error=str(e))
        
    # Check Redis
    try:
        if db_manager.redis_client:
            await db_manager.redis_client.ping()
            redis_ok = True
    except Exception as e:
        logger.error("healthcheck_redis_failed", error=str(e))
        
    status_str = "healthy" if db_ok and redis_ok else "unhealthy"
    
    return {
        "status": status_str,
        "services": {
            "mongodb": "online" if db_ok else "offline",
            "redis": "online" if redis_ok else "offline"
        }
    }

# Register API routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(workspaces.router, prefix=f"{settings.API_V1_STR}/workspaces", tags=["Workspaces"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["Documents"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["Chat"])
