from dotenv import load_dotenv
import os
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
# Rate Limiter
from app.core.route_limiters import limiter
# Routers
from app.routes.health import router as health_router
from app.routes.interview_feedback import router as interview_feedback_router
from app.routes.ai_coach_conversation import router as ai_coach_conversation_router
# CORS Middleware
from app.core.cors_middleware import add_cors_middleware

from loguru import logger

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Service API",
    description="API for the AI Service",
    version="0.1.0",
)
# Add CORS middleware
add_cors_middleware(app)    

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
