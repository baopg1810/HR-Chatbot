from contextlib import asynccontextmanager
from pathlib import Path
import uuid
from dotenv import load_dotenv

# Load environment variables into os.environ before anything else
load_dotenv(".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.api.v1.router import api_router
from app.core.config import get_settings

# Import all models to register them with Base.metadata
import app.models  # noqa: F401
from app.database.base import Base
from app.models.user import User

from app.database.session import engine, get_db_context
from app.core.security import get_password_hash
settings = get_settings()
frontend_dist = Path("frontend/dist")


async def init_db():
    if settings.app_env == "production":
        print("Skipping automatic table creation and demo seeding in production.")
        return

    print("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        print("Seeding demo users...")
        async with get_db_context() as db:
            # Seed employee
            res = await db.execute(select(User).filter(User.email == "employee@example.com"))
            if not res.scalars().first():
                emp = User(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                    email="employee@example.com",
                    employee_code="EMP001",
                    full_name="Nguyen Van An",
                    department="HR",
                    position="Staff",
                    employment_type="Full-time",
                    role="employee",
                    is_active=True,
                    password_hash=get_password_hash("employee123")
                )
                db.add(emp)
                
            # Seed admin
            res = await db.execute(select(User).filter(User.email == "admin@example.com"))
            if not res.scalars().first():
                adm = User(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                    email="admin@example.com",
                    employee_code="ADM001",
                    full_name="Tran Thi HR",
                    department="HR",
                    position="Manager",
                    employment_type="Full-time",
                    role="admin",
                    is_active=True,
                    password_hash=get_password_hash("admin123")
                )
                db.add(adm)
                
            await db.commit()
        print("Database initialization and seeding complete.")
    except Exception as e:
        print(f"Error during database initialization: {e}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name} in {settings.app_env} mode (Refactored)")
    await init_db()
    yield
    print("Shutting down...")


app = FastAPI(
    title="HR Helpdesk AI",
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

app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/live")
async def health_live():
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/ready")
async def health_ready():
    checks = {
        "database": "unknown",
        "vector_store": "unknown",
        "model_provider": "configured" if (settings.google_api_key or settings.google_api_keys) else "missing",
    }
    ready = True

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        ready = False
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        settings.chroma_persist_dir and Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        checks["vector_store"] = "ok"
    except Exception as exc:
        ready = False
        checks["vector_store"] = f"error: {exc.__class__.__name__}"

    if settings.app_env == "production" and checks["model_provider"] != "configured":
        ready = False

    return {"status": "ready" if ready else "not_ready", "env": settings.app_env, "checks": checks}


@app.get("/app", include_in_schema=False)
async def frontend_app():
    if (frontend_dist / "index.html").exists():
        return FileResponse(frontend_dist / "index.html")
    return FileResponse("backend/app/static/hr-helpdesk.html")


if frontend_dist.exists():
    app.mount("/app", StaticFiles(directory=frontend_dist, html=True), name="react_frontend")
