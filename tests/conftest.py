from unittest.mock import AsyncMock
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Keep test resets away from the local development Chroma store in data/chroma.
os.makedirs("./data", exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"

os.environ["CHROMA_PERSIST_DIR"] = tempfile.mkdtemp(prefix="c2-app-test-chroma-")


from app.main import app, init_db
from app.services.rate_limit import reset_chat_rate_limiter
import asyncio

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



@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
