from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.route_limiters import limiter
from app.routes.health import router as health_router

from loguru import logger

# Initialize FastAPI app
app = FastAPI(
    title="AI Service API",
    description="API for the AI Service",
    version="0.1.0",
)

# Add rate limiter to the app
try:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except Exception as e:
    logger.error(f"Error adding rate limiter: {e}")

# Include routers
app.include_router(health_router)
