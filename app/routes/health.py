from fastapi import APIRouter
from app.core.RouteLimiters import limiter
from app.schemas.HealthResponse import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def health():
    return {"status": "ok"} 
