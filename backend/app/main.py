"""
FastAPI application entry point.
Initializes configuration, database, middleware, routers, and handles lifespan events.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse, HTMLResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.middleware import setup_middleware
from app.db.base import init_db, close_db
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    settings = get_settings()
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Initialize DB (creates SQLite tables automatically)
    await init_db()
        
    yield
    
    # Shutdown sequence
    await close_db()


app = FastAPI(
    title=get_settings().APP_NAME,
    version=get_settings().APP_VERSION,
    description=get_settings().APP_DESCRIPTION,
    lifespan=lifespan,
)

# Setup middleware (CORS, logging, rate limiting)
setup_middleware(app)
# Fix for Hugging Face Spaces nginx buffering breaking SSE/streaming
@app.middleware("http")
async def add_streaming_headers(request: Request, call_next):
    response = await call_next(request)
    if "text/event-stream" in response.headers.get("content-type", ""):
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Cache-Control"] = "no-cache"
    return response
# Include core API routes
app.include_router(api_router)

# Register custom exception handler to translate raw Pydantic 422 validation errors into friendly 400 Bad Request messages
# pyrefly: ignore [missing-import]
from fastapi.exceptions import RequestValidationError
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    for err in errors:
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        msg = err.get("msg", "Invalid value")
        error_messages.append(f"{loc}: {msg}" if loc else msg)
    
    return JSONResponse(
        status_code=400,
        content={
            "detail": "; ".join(error_messages)
        }
    )


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": get_settings().APP_NAME,
        "deployment_mode": "local",
    }


# Static files / Frontend routing for Single Container HF Spaces deployment
static_dir = Path(__file__).resolve().parent.parent / "static"

if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    # Fallback to index.html for React SPA client-side routing
    @app.get("/{fallback_path:path}", response_class=FileResponse)
    async def serve_spa_frontend(fallback_path: str):
        # Prevent intercepting API routes or files
        if fallback_path.startswith("api/") or fallback_path.startswith("docs") or fallback_path.startswith("openapi.json"):
            return None
        
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        
        return HTMLResponse(
            content="<h1>Frontend build is missing.</h1><p>Run frontend build script to populate files.</p>",
            status_code=404
        )
else:
    @app.get("/", response_class=HTMLResponse)
    async def index_fallback():
        return HTMLResponse(
            content="""
            <html>
                <head><title>Knowledge Hub AI API</title></head>
                <body style="font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background-color: #0f172a; color: #f8fafc;">
                    <h1>Welcome to Knowledge Hub AI API</h1>
                    <p>API documentation is available at <a href="/docs" style="color: #38bdf8;">/docs</a>.</p>
                </body>
            </html>
            """
        )
