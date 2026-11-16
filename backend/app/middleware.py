from typing import Final

from starlette.datastructures import MutableHeaders
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


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_api = str(scope["path"]).startswith("/api/")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in COMMON_SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                if is_api:
                    for name, value in API_SECURITY_HEADERS.items():
                        headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)
