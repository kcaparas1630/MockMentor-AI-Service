from pydantic import BaseModel

class HealthResponse(BaseModel):
    """
    Schema for health check endpoint responses.
    """
    status: str
