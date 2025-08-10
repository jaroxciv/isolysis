import pytest
from pathlib import Path
from loguru import logger
import sys

# Configure loguru for tests
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)


@pytest.fixture(scope="session")
def testdir() -> str:
    return str(Path(__file__).parent.parent.resolve())


def pytest_addoption(parser):
    parser.addoption(
        "--api-url",
        action="store",
        default="http://localhost:8000",
        help="Base URL for Isolysis API",
    )


@pytest.fixture(scope="session")
def api_url(request):
    return request.config.getoption("--api-url")


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "api: marks tests that require API")
    config.addinivalue_line("markers", "integration: marks integration tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark API tests"""
    api_marker = pytest.mark.api
    for item in items:
        if "test_api" in item.nodeid:
            item.add_marker(api_marker)
