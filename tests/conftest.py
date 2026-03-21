import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from dotenv import load_dotenv
from pathlib import Path

from config import get_settings
from main import create_app
from database import get_db
from users.enums import UserGroupEnum
from users.models import UserGroup

from tests.settings import get_test_settings
from tests.utils.db import create_test_engine, drop_test_engine


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env.test")


@pytest.fixture(scope="session")
def test_app():
    """Returns a FastAPI application instance with testing=True.

    This means that the SlowAPI middleware is not added, and rate limiting
    is disabled.

    This fixture has session scope, meaning it is only invoked once per
    test session.
    """
    return create_app(testing=True)


@pytest.fixture(autouse=True)
def disable_slowapi_decorators(monkeypatch):
    """Disables all rate limiting decorators in tests.

    This is useful for tests that don't care about rate limiting, and
    want to test the underlying code without the rate limiter getting in
    the way.

    The `@limiter.limit` decorator is a no-op in tests that use this
    fixture.

    This fixture has autouse=True, meaning it is automatically applied
    to all tests in the test session. If you want to test rate limiting,
    you will need to disable this fixture by using the
    `@pytest.mark.usefixtures` marker and passing an empty list of fixtures.

    For example:
    @pytest.mark.usefixtures([])
    def test_my_test():
        # this test will use rate limiting
        pass
    """

    # Make all @limiter.limit decorators no‑ops in tests
    def no_limit(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    monkeypatch.setattr("rate_limiting.limiter.limit", no_limit)


# -----------------------------
# PostgreSQL URL from pytest-postgresql
# -----------------------------
@pytest.fixture(scope="session")
def pg_url(
    postgresql_proc,
):  # session-scoped fixture. starts a Postgres instance on its first use and stops it when all tests are finished
    """Returns a PostgreSQL URL string from the pytest-postgresql fixture.

    The URL is generated from the pytest-postgresql fixture's user, password,
    host, port, and database name.

    This fixture has session scope, meaning it is only invoked once per
    test session.

    :param postgresql_proc: The pytest-postgresql fixture.
    :return: A PostgreSQL URL string.
    :rtype: str
    """
    return (
        f"postgresql+asyncpg://{postgresql_proc.user}:"
        f"{postgresql_proc.password}@{postgresql_proc.host}:"
        f"{postgresql_proc.port}/{postgresql_proc.dbname}"
    )


# -----------------------------
# Create test engine + schema
# NOTE: function scope so engine is bound to the same loop as the test
# -----------------------------
@pytest_asyncio.fixture
async def test_engine(pg_url):
    """Creates a test PostgreSQL engine and drops it after the test is finished.

    This fixture creates a test PostgreSQL engine using the given
    PostgreSQL URL.
    It then yields the engine to the test, and finally drops the engine after
    the test is finished.

    :param pg_url: A PostgreSQL URL string.
    :return: A test PostgreSQL engine.
    :rtype: sqlalchemy.ext.asyncio.AsyncEngine
    """
    engine = await create_test_engine(pg_url)
    try:
        yield engine
    finally:
        await drop_test_engine(engine)


# -----------------------------
# Override settings for tests
# -----------------------------
@pytest.fixture(autouse=True)
def override_settings(test_app):
    """Overrides the get_settings dependency with get_test_settings.

    This fixture overrides the get_settings dependency with get_test_settings,
    which returns TestSettings. It then yields the test app, and finally
    restores the original dependency after the test is finished.

    This fixture has autouse=True, meaning it is automatically applied to all
    tests in the test session. If you want to test with different settings,
    you will need to disable this fixture by using the
    `@pytest.mark.usefixtures` marker and passing an empty list of fixtures.

    For example:
    @pytest.mark.usefixtures([])
    def test_my_test():
        # this test will use the real get_settings
        pass
    """
    test_app.dependency_overrides[get_settings] = lambda: get_test_settings()
    yield
    test_app.dependency_overrides.pop(get_settings, None)


# -----------------------------
# Correct DB override (per-request session)
# -----------------------------
@pytest.fixture(autouse=True)
def override_db_dependency(test_app, test_engine):
    """Overrides the get_db dependency with an async session maker that uses
    the test_engine.

    This fixture overrides the get_db dependency with an async session maker
    that uses the test_engine. It then yields the test app, and finally
    restores the original dependency after the test is finished.

    This fixture has autouse=True, meaning it is automatically applied to all
    tests in the test session. If you want to test with a different database
    dependency, you will need to disable this fixture by using the
    `@pytest.mark.usefixtures` marker and passing an empty list of fixtures.

    For example:
    @pytest.mark.usefixtures([])
    def test_my_test():
        # this test will use the real get_db
        pass
    """
    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
        class_=AsyncSession,
    )

    async def _override_get_db():
        async with async_session() as session:
            yield session

    test_app.dependency_overrides[get_db] = _override_get_db
    yield
    test_app.dependency_overrides.pop(get_db, None)


# -----------------------------
# HTTP client using ASGITransport
# -----------------------------
@pytest_asyncio.fixture
async def client(test_app):
    """An async fixture. Yields an AsyncClient instance connected to the test app.

    The client is configured to use the ASGITransport, which allows the client
    to communicate with the test app over an in-memory ASGI server.
    The base URL of the client is set to "http://test".

    This fixture is useful for testing the API endpoints of the test app.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# -----------------------------
# Moto S3 mock
# -----------------------------
@pytest.fixture
def s3_mock():
    """A fixture that sets up a Moto mock for S3, which can be used to test code
    that interacts with S3.

    The fixture uses `@pytest.fixture` marker, that means it's automatically
    invoked by Pytest when a test function asks for the `s3_mock` argument.

    The fixture yields nothing, so it can be used as a marker to indicate that
    a test needs a Moto mock for S3.

    When this fixture is invoked, it sets up a Moto mock for S3, which allows
    tests to run without actually interacting with S3.

    This fixture is useful for testing code that interacts with S3, such as
    S3-compatible storage clients or upload/download functions.
    """
    with mock_aws():
        yield


@pytest_asyncio.fixture
async def default_user_group(test_engine):
    """An async fixture that yields a UserGroup instance with name USER.

    The fixture sets up a UserGroup instance with name USER in the test database,
    and yields the instance to the test.

    This fixture is useful for testing code that interacts with UserGroup instances,
    such as user registration or authentication functions.

    The fixture ensures that the UserGroup instance is properly initialized and
    deleted after the test is finished.

    :param test_engine: The test database engine.
    :return: A UserGroup instance with name USER.
    :rtype: UserGroup
    """
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        group = UserGroup(name=UserGroupEnum.USER)
        session.add(group)
        await session.commit()
        yield group


@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch):
    def fake_delay(*args, **kwargs):
        return None

    # Registration email
    monkeypatch.setattr(
        "auth.service.send_activation_email.delay",
        fake_delay,
        raising=False,
    )

    # Activation-complete email
    monkeypatch.setattr(
        "auth.service.send_activation_complete_email.delay",
        fake_delay,
        raising=False,
    )

    # Password reset
    monkeypatch.setattr(
        "auth.service.send_password_reset_email.delay",
        fake_delay
    )

    monkeypatch.setattr(
        "auth.service.send_password_reset_complete_email.delay",
        fake_delay
    )
