import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    document_id: str = os.getenv("DOCUMENT_ID", "clouds_doc_v1")
    document_path: Path = Path(os.getenv("DOCUMENT_PATH", "src/data/DOCUMENT.md"))
    database_path: Path = Path(os.getenv("DATABASE_PATH", "src/data/app.db"))
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_device: str = "cpu"
    top_k: int = int(os.getenv("TOP_K", "3"))

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"


settings = Settings()
