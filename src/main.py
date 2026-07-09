from fastapi import FastAPI
import uvicorn

from src.api.chat import router as chat_router
from src.api.summaries import router as summaries_router
from src.api.changes import router as changes_router
from src.api.documents import router as documents_router
from src.api.evidence import router as evidence_router
from src.api.verification import router as verification_router
from src.core.config import settings
from src.db.bootstrap import bootstrap_database

app = FastAPI(
    title="Agentic Document Chat",
    version="0.3.0",
)

bootstrap_database(settings.document_path)

app.include_router(chat_router)
app.include_router(summaries_router)
app.include_router(changes_router)
app.include_router(documents_router)
app.include_router(verification_router)
app.include_router(evidence_router)


@app.get("/")
def root():
    return {
        "service": "Agentic Document Chat",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
