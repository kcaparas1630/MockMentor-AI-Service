from fastapi import APIRouter, Request
from app.core.route_limiters import limiter
from app.schemas.health_response import HealthResponse
from loguru import logger
router = APIRouter(
    prefix="/api",
    tags=["health"]
)

@router.get("/health", response_model=HealthResponse)
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def health(request: Request):
    """
    Request parameter is required for rate limiting.
    """
    logger.info("Health check endpoint called")
    return {"status": "ok"} 
