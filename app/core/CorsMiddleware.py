from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

origins = [
    "https://ai-interview-frontend-244697793005.us-east1.run.app",
    "https://ai-interview-typescript-server-244697793005.us-east1.run.app"
]

def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware added")
