from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_409_CONFLICT

class BadRequest(HTTPException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, detail=detail)

class NotFound(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=HTTP_404_NOT_FOUND, detail=detail)

class InternalServerError(HTTPException):
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class Unauthorized(HTTPException):
    def __init__(self, detail: str = "Unauthorized access"):
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, detail=detail)

class DuplicateRecordError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail
        )
class WeakPasswordError(BadRequest):
    def __init__(self, detail: str = "The provided password is weak. Password must contain an upper case character, numeric character, and a non-alphanumeric character."):
        super().__init__(detail=detail)

class DuplicateUserError(DuplicateRecordError):
    def __init__(self, identifier: str = None):
        detail = f"User {identifier}' already exists." if identifier else "User already exists."
        super().__init__(detail=detail)
class DuplicateInterviewError(DuplicateRecordError):
    def __init__(self, identifier: str = None):
        detail = f"Interview '{identifier}' already exists." if identifier else "Interview already exists."
        super().__init__(detail=detail)
class DuplicateQuestionError(DuplicateRecordError):
    def __init__(self, identifier: str = None):
        detail = f"Question '{identifier}' already exists." if identifier else "Question already exists."
        super().__init__(detail=detail)
class UserNotFound(NotFound):
    def __init__(self, identifier: str = None):
        detail = f"User not found." if identifier else "User not found."
        super().__init__(detail=detail)
class UserDisabled(Unauthorized):
    def __init__(self, identifier: str = None):
        detail = f"User is disabled." if identifier else "User is disabled."
        super().__init__(detail=detail)
class ValidationError(BadRequest):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail=detail)
