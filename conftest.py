"""Pytest configuration ensuring complete database isolation across all test suites."""
import os
import tempfile
import shutil
import pytest

_test_temp_dir = tempfile.mkdtemp(prefix="cbtts_isolated_test_")
_test_db_path = os.path.join(_test_temp_dir, "pytest_sandbox.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Ensure tests run strictly against an isolated temporary SQLite database."""
    yield _test_db_path
    try:
        shutil.rmtree(_test_temp_dir, ignore_errors=True)
    except Exception:
        pass

