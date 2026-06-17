from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config import get_settings

settings = get_settings()
frontend_dist = Path("frontend/dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    print("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="AI assistant for HR policy Q&A, employee self-service, and HR escalation workflows.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="src/static"), name="static")
app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/app/")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/app", include_in_schema=False)
async def frontend_app():
    if (frontend_dist / "index.html").exists():
        return FileResponse(frontend_dist / "index.html")
    return FileResponse("src/static/hr-helpdesk.html")


if frontend_dist.exists():
    app.mount("/app", StaticFiles(directory=frontend_dist, html=True), name="react_frontend")
