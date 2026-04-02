import asyncio
import os
import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from fastapi import Depends
from api.routes import regulations, actions, controls, health, stream, upload, alerts, cve, compliance, ask, reports
from api.auth import require_api_key
from config import settings

logger = structlog.get_logger()

# ─── Prometheus Metrics ───────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "redforge_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "redforge_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"],
)
DOCUMENTS_PROCESSED = Counter(
    "redforge_documents_processed_total",
    "Total regulatory documents processed",
    ["jurisdiction", "relevant"],
)
ACTION_ITEMS_CREATED = Counter(
    "redforge_action_items_total",
    "Total action items generated",
    ["priority"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("redforge_api_starting", version="0.1.0")

    # Ensure all DB tables exist (safe to call repeatedly — uses CREATE IF NOT EXISTS)
    try:
        from org_context.models.database import create_tables
        create_tables()
        logger.info("db_tables_ensured")
    except Exception as e:
        logger.warning("db_tables_init_failed", error=str(e))

    # Start proactive CVE scanner background loop
    scan_interval = int(os.environ.get("SCAN_INTERVAL_HOURS", "6"))
    scanner_task = None
    try:
        from monitoring.proactive_scanner import proactive_scan_loop
        scanner_task = asyncio.create_task(proactive_scan_loop(interval_hours=scan_interval))
        logger.info("proactive_scanner_task_started", interval_hours=scan_interval)
    except Exception as e:
        logger.warning("proactive_scanner_not_started", error=str(e))

    # Start regulatory horizon scanner background loop
    horizon_interval = int(os.environ.get("HORIZON_SCAN_INTERVAL_HOURS", "12"))
    horizon_task = None
    try:
        from monitoring.horizon_scanner import horizon_scan_loop
        horizon_task = asyncio.create_task(horizon_scan_loop(interval_hours=horizon_interval))
        logger.info("horizon_scanner_task_started", interval_hours=horizon_interval)
    except Exception as e:
        logger.warning("horizon_scanner_not_started", error=str(e))

    yield

    for task in [scanner_task, horizon_task]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    logger.info("redforge_api_shutdown")


app = FastAPI(
    title="Red Forge — Regulatory Compliance API",
    description="AI-Powered Regulatory Compliance Monitoring",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://32.192.255.100",
]
# Add custom origins from env if set (comma-separated)
_extra_origins = os.environ.get("CORS_ORIGINS", "")
if _extra_origins:
    _cors_origins.extend([o.strip() for o in _extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response


# ─── Routes ───────────────────────────────────────────────────────────────────
# /health and /metrics are unauthenticated (used by load balancers / Prometheus)
app.include_router(health.router, prefix="/health", tags=["health"])

# All /api/v1/* routes require X-API-Key when API_KEY is set in .env
_auth = [Depends(require_api_key)]
app.include_router(regulations.router, prefix="/api/v1/regulations", tags=["regulations"], dependencies=_auth)
app.include_router(actions.router, prefix="/api/v1/actions", tags=["actions"], dependencies=_auth)
app.include_router(controls.router, prefix="/api/v1/controls", tags=["controls"], dependencies=_auth)
app.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"], dependencies=_auth)
app.include_router(upload.router, prefix="/api/v1/org", tags=["org"], dependencies=_auth)
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"], dependencies=_auth)
app.include_router(cve.router, prefix="/api/v1/cve", tags=["cve"], dependencies=_auth)
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["compliance"], dependencies=_auth)
app.include_router(ask.router, prefix="/api/v1/ask", tags=["ask"], dependencies=_auth)
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"], dependencies=_auth)


@app.get("/", include_in_schema=False)
def root():
    return {"service": "Red Forge API", "version": "0.1.0", "status": "running"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
