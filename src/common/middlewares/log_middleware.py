import time
from typing import Callable

import orjson
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.common.configs.logging import get_logger, set_request_id
from src.common.configs.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Headers redacted from logs to avoid leaking credentials.
_REDACTED_REQUEST_HEADERS = {"authorization", "cookie", "x-api-key"}

# Methods whose body is worth logging (debug only).
_BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log one consolidated line per HTTP request.

    Under async concurrency many requests are in flight at once, so logging the
    request on the way in and the response on the way out would interleave the
    two halves of a single request with other requests' lines. Instead, the
    request and response details are gathered while the request is processed and
    emitted as a single combined, request-id-correlated line.

    Only the response status and timing are logged: capturing the response body
    would force the log to wait until the body finished streaming. In production
    (debug=False) request headers and body are omitted too, as they can carry
    secrets/PII and buffering the body adds latency on every request.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        set_request_id()

        # Capture request details while the body is still readable.
        request_log = await self._build_request_log(request)

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(f"{request_log} - FAILED after {process_time:.4f}s: {exc}")
            raise

        process_time = time.time() - start_time
        logger.info(
            f"{request_log} | RESPONSE: Status: {response.status_code} "
            f"- Time: {process_time:.4f}s"
        )
        return response

    async def _build_request_log(self, request: Request) -> str:
        parts = [f"REQUEST: {request.method}", f"URL: {request.url}"]

        if settings.debug:
            headers = self._safe_headers(request.headers, _REDACTED_REQUEST_HEADERS)
            parts.append(f"Headers: {headers}")
            if request.method in _BODY_METHODS:
                parts.append(f"Body: {await self._get_request_body(request)}")

        return " - ".join(parts)

    @staticmethod
    def _safe_headers(headers, redacted: set[str]) -> dict[str, str]:
        return {k: v for k, v in headers.items() if k.lower() not in redacted}

    @staticmethod
    async def _get_request_body(request: Request) -> str:
        """Safely extract the request body as a string."""
        try:
            body = await request.body()
        except Exception as exc:
            return f"<error reading body: {exc}>"

        if not body:
            return "<empty>"
        try:
            return orjson.dumps(orjson.loads(body), option=orjson.OPT_INDENT_2).decode(
                "utf-8"
            )
        except orjson.JSONDecodeError, UnicodeDecodeError:
            try:
                return body.decode("utf-8")
            except UnicodeDecodeError:
                return f"<binary data: {len(body)} bytes>"
