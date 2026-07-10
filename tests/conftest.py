import pytest

from src.core.config import settings
from src.db.bootstrap import bootstrap_database
from src.db.session import configure_database


@pytest.fixture()
def temp_database(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    database_path = tmp_path / "app.db"
    configure_database(f"sqlite:///{database_path.as_posix()}")
    bootstrap_database(settings.document_path)

    yield database_path
