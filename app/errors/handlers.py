from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from sqlalchemy.exc import IntegrityError
from app.errors.exceptions import DuplicateUserError, DuplicateInterviewError, DuplicateQuestionError

def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )
def database_integrity_handler(request: Request, exc: IntegrityError):
    """
    Handle SQLAlchemy integrity constraint violations.
    
    Converts database errors into user-friendly responses, with special
    handling for duplicate key violations.
    
    Args:
        request: FastAPI request instance
        exc: IntegrityError from SQLAlchemy
        
    Returns:
        JSONResponse with 400 status and user-friendly error message
        
    Raises:
        DuplicateUserError | DuplicateInterviewError | DuplicateQuestionError: For duplicate key violations
    """
    error_msg = str(exc.orig).lower()
    
    if "duplicate key" in error_msg or "unique constraint" in error_msg:
        if "users" in error_msg or "firebase_uid" in error_msg:
            raise DuplicateUserError()
        elif "interviews" in error_msg:
            raise DuplicateInterviewError()
        elif "questions" in error_msg:
            raise DuplicateQuestionError()
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Database error",
            "message": "Data constraint violation",
            "hint": "Please check your data and try again"
        }
    )
