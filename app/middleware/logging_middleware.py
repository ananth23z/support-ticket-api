"""
app/middleware/logging_middleware.py
====================================
WHAT:  Code that runs around EVERY request: logs method, path, status and duration,
       and adds an `X-Process-Time` header to the response.
WHY:   Middleware is for "cross-cutting concerns" - things every endpoint needs
       but no single endpoint should be responsible for (logging, timing, CORS...).

HOW IT WORKS (the "onion" / pipeline model):

    request  ->  [ middleware: before ]  ->  router -> endpoint
    response <-  [ middleware: after  ]  <-  (response comes back out)

    `await call_next(request)` = "pass the request to the next layer and wait
    for the response". Code before it runs on the way IN, code after on the way OUT.

ASP.NET ANALOGY:
    Exactly like `app.Use(async (context, next) => { ...; await next(); ... })`
    or a class with `InvokeAsync(HttpContext context, RequestDelegate next)`.
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()  # high-precision timer

        response = await call_next(request)  # <-- the rest of the app runs here

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method, request.url.path, response.status_code, duration_ms,
        )
        return response
