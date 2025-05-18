from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

# Set up rate limiter (e.g., 5 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
logger.info("Rate limiter initialized")
