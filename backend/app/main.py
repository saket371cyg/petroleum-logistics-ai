import logging
from time import perf_counter
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analytics, auth, compliance, dispatch, fleet, forecast, inventory, orders, refinery
from app.core.config import settings

logger = logging.getLogger("petro_dealer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

_login_attempts: Dict[str, list[float]] = {}

app = FastAPI(
    title="Agentic AI Decision Intelligence Platform — Petroleum Dealer Logistics",
    description="Dealer-facing AI decision-support platform for fuel demand, inventory, and dispatch.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_security_and_logging(request: Request, call_next):
    start = perf_counter()
    path = request.url.path

    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
            logger.warning("Rejected oversized request: %s %s (%s bytes)", request.method, path, content_length)
            return JSONResponse(status_code=413, content={"detail": "Request payload too large."})

    if path == "/auth/login":
        client_ip = request.client.host if request.client else "unknown"
        now = perf_counter()
        bucket = _login_attempts.setdefault(client_ip, [])
        bucket[:] = [ts for ts in bucket if now - ts < settings.LOGIN_RATE_WINDOW_SECONDS]
        if len(bucket) >= settings.LOGIN_RATE_LIMIT:
            logger.warning("Login rate limit hit for %s", client_ip)
            return JSONResponse(status_code=429, content={"detail": "Too many login attempts. Please retry later."})
        bucket.append(now)

    try:
        response = await call_next(request)
    except RequestValidationError as exc:  # pragma: no cover - FastAPI validation path
        logger.warning("Validation error at %s: %s", path, exc)
        raise

    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "request path=%s method=%s status=%s duration_ms=%s",
        path,
        request.method,
        getattr(response, "status_code", 500),
        duration_ms,
    )
    return response


app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(forecast.router)
app.include_router(orders.router)
app.include_router(fleet.router)
app.include_router(refinery.router)
app.include_router(dispatch.router)
app.include_router(compliance.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "petro-dealer-ai-platform", "synthetic_data": True}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "configured",
        "jwt_secret_configured": settings.JWT_SECRET_KEY not in {"dev_secret_key_do_not_use_in_prod", "change_this_secret_in_production"},
        "synthetic_data": True,
    }
