"""
Description: 
This module sets up a rate limiter for the application using SlowAPI.
It initializes a Limiter instance with a key function to identify clients by their IP address and sets default limits for requests.

Dependencies:
- slowapi: For rate limiting functionality.
- slowapi.util: For utility functions like get_remote_address to retrieve the client's IP address.
- loguru: For logging information about the rate limiter initialization.

Author: @kcaparas1630
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

# Set up rate limiter (e.g., 5 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
logger.info("Rate limiter initialized")
