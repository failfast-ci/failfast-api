from typing import Any, Optional

from fastapi import HTTPException


class APIException(HTTPException):
    status_code: int = 500
    errorcode: str = "internal-error"
    payload: dict[str, Any]

    def __init__(self, message: str, payload: Optional[dict[str, Any]] = None) -> None:
        if not payload:
            payload = {}
        self.payload: dict[str, Any] = dict(payload)
        self.message = message
        super().__init__(status_code=self.status_code, detail=self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.errorcode,
            "message": self.message,
            "details": self.payload,
        }

    def __str__(self) -> str:
        return self.message


class InvalidUsage(APIException):
    status_code = 400
    errorcode = "invalid-usage"


class InvalidParams(APIException):
    status_code = 422
    errorcode = "invalid-parameters"


class ResourceNotFound(APIException):
    status_code = 404
    errorcode = "resource-not-found"


class Forbidden(APIException):
    status_code = 403
    errorcode = "forbidden"


class UnauthorizedAccess(APIException):
    status_code = 401
    errorcode = "unauthorized-access"


class Unsupported(APIException):
    status_code = 501
    errorcode = "unsupported"


class Unexpected(APIException):
    status_code = 500
    errorcode = "unexpected-error"
