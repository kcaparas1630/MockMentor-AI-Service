from dotenv import load_dotenv
import os
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
# Rate Limiter
from app.core.route_limiters import limiter
# Routers
from app.routes.health import router as health_router
from app.routes.interview_feedback import router as interview_feedback_router
from app.routes.ai_coach_conversation import router as ai_coach_conversation_router
# CORS Middleware
from app.core.cors_middleware import add_cors_middleware
# Logger
from loguru import logger
# Database
from app.database import create_tables
# Error Handling
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from sqlalchemy.exc import IntegrityError

from app.errors.handlers import http_exception_handler, generic_exception_handler, database_integrity_handler

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    try:
        create_tables()
        logger.info("Application startup completed successfully")

        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    
    yield
    
    # Shutdown (if needed)
    logger.info("Application shutdown")

# Initialize FastAPI app
app = FastAPI(
    title="AI Service API",
    description="API for the AI Service",
    version="0.1.0",
    lifespan=lifespan
)
# Add CORS middleware
add_cors_middleware(app)    

# Centralized error handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(IntegrityError, database_integrity_handler )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

# Add rate limiter to the app
try:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except Exception as e:
    logger.error(f"Error adding rate limiter: {e}")

# Include routers
app.include_router(health_router)
app.include_router(interview_feedback_router)
app.include_router(ai_coach_conversation_router)
