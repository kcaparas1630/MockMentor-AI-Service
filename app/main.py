from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.util import _rate_limit_exceeded_handler
from app.core.RouteLimiters import limiter
from app.routes.health import router as health_router

# Initialize FastAPI app
app = FastAPI()

# Add rate limiter to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(health_router)
