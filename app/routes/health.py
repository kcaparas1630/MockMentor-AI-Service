"""
Health check endpoint for the application.

Description:
This module defines a FastAPI route for checking the health status of the application.

Arguments:
- request: An instance of Request, required for rate limiting.

Returns:
- A JSON response with the status of the application, typically {"status": "ok"}.

Dependencies:
- fastapi: For creating the FastAPI application and defining routes.
- app.core.route_limiters: For rate limiting functionality.
- app.schemas.health_response: For defining the response model.
- loguru: For logging information about the health check endpoint.

Author: @kcaparas1630

"""
from fastapi import APIRouter, Request
from ..core.route_limiters import limiter
from ..schemas.health_response import HealthResponse
from loguru import logger
router = APIRouter(
    prefix="/api",
    tags=["health"],
    responses={404: {"description": "Not found"}}
)

@router.get("/health", response_model=HealthResponse)
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def health(request: Request):
    """
    Request parameter is required for rate limiting.
    """
    logger.info("Health check endpoint called")
    return {"status": "ok"} 
