"""
Description:
Module for adding CORS middleware to FastAPI application.

Arguments:
- app: FastAPI application instance to which CORS middleware will be added.

Returns:
- None, but modifies the app to allow cross-origin requests from specified origins.

Dependencies:
- fastapi: For creating the FastAPI application and adding middleware.
- fastapi.middleware.cors: For CORS middleware functionality.
- loguru: For logging information about the middleware setup.

Author: @kcaparas1630
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

origins = [
    "https://ai-interview-frontend-244697793005.us-east1.run.app",
    "https://ai-interview-typescript-server-244697793005.us-east1.run.app"
]

def add_cors_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware added")
