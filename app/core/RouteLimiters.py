from slowapi import Limiter
from slowapi.util import get_remote_address


# Set up rate limiter (e.g., 5 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
