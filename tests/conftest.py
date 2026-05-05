import os
import tempfile
from pathlib import Path


os.environ.setdefault("LLM_PROVIDER", "mock")
TEST_DIR = Path(tempfile.mkdtemp(prefix="llm-observatory-tests-"))
os.environ["LLM_OBSERVATORY_DB_PATH"] = str(TEST_DIR / "test_metrics.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR / 'test_observatory.db'}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-thirty-two-bytes")
os.environ.setdefault("API_KEY_PEPPER", "test-api-key-pepper-with-at-least-thirty-two-bytes")
