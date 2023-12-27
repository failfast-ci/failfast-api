from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ..exception import UnauthorizedAccess


class TokenAuthMiddleware:
    def __init__(self, app: ASGIApp, token: str = "") -> None:
        self.token = token
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = Headers(scope=scope)
        if "token" not in headers or headers["token"] != self.token:
            error = UnauthorizedAccess("NoAuth")
            await JSONResponse(
                {"error": error.to_dict()}, status_code=error.status_code
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)
        return
