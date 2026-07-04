import asyncio
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Keep test resets away from the local development Chroma store in data/chroma.
os.makedirs("./data", exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"

os.environ["CHROMA_PERSIST_DIR"] = tempfile.mkdtemp(prefix="c2-app-test-chroma-")


from app.core.config import Settings

os.environ.setdefault("ONLINE_LLM_TESTS", "1" if Settings().online_llm_tests else "0")

from app.config import get_settings
from app.main import app, init_db
from app.services.rate_limit import reset_chat_rate_limiter


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _require_online_provider_credentials() -> None:
    if not _truthy_env("ONLINE_LLM_TESTS"):
        return

    settings = get_settings()
    missing = []
    if not (settings.google_api_key or settings.google_api_keys):
        missing.append("GOOGLE_API_KEY or GOOGLE_API_KEYS")
    if not settings.cohere_api_key:
        missing.append("COHERE_API_KEY")
    if settings.openai_safeguard_enabled:
        if settings.safeguard_provider == "groq" and not (settings.groq_api_key or settings.groq_api_keys):
            missing.append("GROQ_API_KEY or GROQ_API_KEYS")
        if settings.safeguard_provider == "openai" and not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")

    if missing:
        raise RuntimeError(
            "ONLINE_LLM_TESTS=1 requires real provider credentials in .env or environment: "
            + ", ".join(missing)
            + ". Set ONLINE_LLM_TESTS=0 only when you intentionally want deterministic offline fallback."
        )


_require_online_provider_credentials()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    yield res
    res.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_database():
    await init_db()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    reset_chat_rate_limiter()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    reset_chat_rate_limiter()
