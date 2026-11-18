from typing import Final

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

COMMON_SECURITY_HEADERS: Final = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

# Not applied outside /api/: Swagger UI loads assets from a CDN and would break under this CSP.
API_SECURITY_HEADERS: Final = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


def security_headers_for(path: str) -> dict[str, str]:
    if path.startswith("/api/"):
        return {**COMMON_SECURITY_HEADERS, **API_SECURITY_HEADERS}

    return dict(COMMON_SECURITY_HEADERS)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers_for_path = security_headers_for(str(scope["path"]))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in headers_for_path.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


class OriginCheckMiddleware:
    """Reject browser requests whose Origin header is not on the allow-list.

    Requests without an Origin header (curl, server-to-server, same-origin GET) pass through.
    CORS alone only hides responses from the browser; this stops the request from being processed.
    """

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed_origins = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = Headers(scope=scope).get("origin")
        if origin is None or origin in self.allowed_origins:
            await self.app(scope, receive, send)
            return

        response = JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        await response(scope, receive, send)
