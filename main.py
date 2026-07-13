"""
STRIKERS_PROTOCOL RE::INTEL
FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from backend.utils.database import init_db
from backend.routers.auth import router as auth_router
from backend.routers.analysis import router as analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("⬡  STRIKERS_PROTOCOL RE::INTEL starting...")
    await init_db()
    print("✓  Database initialised")
    print(f"✓  API key loaded: {'YES' if os.getenv('ANTHROPIC_API_KEY','').startswith('sk-') else 'NO — check .env'}")
    yield
    # Shutdown
    print("⬡  Shutting down.")


app = FastAPI(
    title       = "STRIKERS_PROTOCOL RE::INTEL",
    description = "Universal Reverse Engineering Intelligence Platform",
    version     = "2.0.0",
    lifespan    = lifespan,
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
)

# ── CORS (allow localhost frontend) ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(analysis_router)

# ── Static files & SPA ───────────────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "frontend", "templates")

@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    index = os.path.join(TEMPLATE_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "RE::INTEL API running. Visit /api/docs"}
