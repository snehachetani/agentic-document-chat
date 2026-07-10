# Agentic Document Chat

Backend service for chatting with a section-based clouds document, verifying sections with external evidence tools, proposing controlled updates, and accepting or rejecting changes with version history.

## Run Locally

```bash
uv sync
uv run uvicorn src.main:app --reload
```

Open Swagger at `http://127.0.0.1:8000/docs`.

Useful environment variables:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
TAVILY_API_KEY=...
DATABASE_PATH=src/data/app.db
```

`OPENAI_API_KEY` enables LLM summaries, rewrite generation, structured chat intent classification, and LlamaIndex retrieval backed by OpenAI embeddings. The default embedding model is `text-embedding-3-small`

## Run Sample Evaluation

The sample evaluation script runs the representative requests from `SAMPLE_REQUESTS.md` against an isolated SQLite database under `src/data`, so it does not modify `src/data/app.db`.

```bash
uv run python scripts/run_sample_requests.py
```

It prints pass/fail checks for document Q&A, section lookup, summarization, rewrite proposals, compare/accept/reject, external verification, evidence-backed proposals, negative cases, and tool traces.

## API Overview

- `POST /chat`
- `GET /documents/{document_id}/sections`
- `GET /documents/{document_id}/sections/{section_id}`
- `GET /documents/{document_id}/sections/{section_id}/history`
- `POST /documents/{document_id}/sections/{section_id}/summary`
- `POST /documents/{document_id}/sections/{section_id}/changes`
- `GET /documents/{document_id}/changes/{change_id}`
- `GET /documents/{document_id}/changes/{change_id}/compare`
- `POST /documents/{document_id}/changes/{change_id}/accept`
- `POST /documents/{document_id}/changes/{change_id}/reject`
- `POST /documents/{document_id}/sections/{section_id}/verify`
- `GET /documents/{document_id}/tool-calls`

Default document id: `clouds_doc_v1`.

## Architecture

The app is split into API routers, RAG/orchestration functions, document/change stores, and external evidence tools.

- API routers live in `src/api`.
- SQLite persistence live in `src/db`.
- Current sections and version history are accessed through `src/documents/store.py`.
- Pending proposals, accept/reject state, and proposal evidence live in `src/changes/store.py`.
- Tavily/offline evidence tools live in `src/tools/search_client.py`.
- Agent orchestration lives in `src/api/chat.py`, `src/rag/intent.py`, `src/rag/engine.py`, `src/rag/rewriter.py`, and `src/rag/verifier.py`.

SQLite is the source of truth after startup. The initial contents are bootstrapped from `src/data/DOCUMENT.md` only when the sections table is empty.

## API And Service Boundaries

The API layer in `src/api` validates request-level inputs, maps service errors to HTTP responses, and returns review-friendly response models. It does not directly mutate section text except through the change store's accept/reject methods.

The service/orchestration layer in `src/rag` handles chat intent routing, retrieval, summarization, rewriting, verification, and evidence-backed proposal generation.

The persistence layer is split between `src/documents/store.py` for current sections/history and `src/changes/store.py` for proposal lifecycle state.

## Agent Orchestration

The `/chat` route uses structured intent classification with OpenAI when `OPENAI_API_KEY` is available, then routes to Q&A, section lookup, summarization, rewrite proposals, verification, or change review. Without a key, it uses a small rule-based fallback so local tests can still run.

Document-only Q&A and section resolution use the current SQLite section state. With `OPENAI_API_KEY`, the app builds a LlamaIndex vector index using OpenAI embeddings and retrieves the most relevant section from that index. Without a key, it uses a small local scoring fallback.

Summaries use the selected current section and do not call external evidence tools.

Rewrite, improve, shorten, and update requests create pending change proposals. They do not directly overwrite section text.

## Tool Selection Logic

Verification requests choose NASA, NOAA, or general search based on the user instruction plus the selected section title. Document-only Q&A, section lookup, summaries, compare, accept, and reject do not call external evidence tools.

NASA/NOAA searches are domain restricted in `src/tools/search_client.py`. If Tavily is unavailable or not configured, the tools return offline NASA/NOAA-style sample evidence so the review workflow remains runnable.

## Document State And Versioning

The canonical startup document is `src/data/DOCUMENT.md`. On first run, its sections are loaded into SQLite. After that, SQLite is the source of truth for current section text and version numbers.

Accepted changes store the previous section text in `section_versions`, increment the current section version, and keep the new text in `sections`.

## Change Proposal Lifecycle

Rewrite/update requests create `pending` proposals containing original text, proposed text, reason, status, and optional evidence. They never modify the section immediately.

Accepting a proposal checks that it is still pending and not stale, writes the old section text to history, updates the section text, increments the version, and marks the proposal `accepted`.

Rejecting a proposal marks it `rejected` and leaves the section unchanged. Repeated accept/reject attempts return a conflict response.

## Citation And Evidence Handling

Evidence-backed verification returns a fact-check summary plus `evidence_used` entries with source title, source URL, supporting text, tool name, and source domain. Tool calls are also persisted and inspectable through `/documents/{document_id}/tool-calls`.

Evidence-backed proposed edits store the same evidence on the change proposal. Prompts instruct the model to use only the original section text and supplied evidence, and the verifier refuses to create an evidence-backed proposal when no evidence is available.

## Resetting Local State

To reset the document, stop the server and remove `src/data/app.db`; the next startup reloads sections from `src/data/DOCUMENT.md`.

```powershell
Remove-Item .\src\data\app.db
uv run uvicorn src.main:app --reload
```

Temporary database files created during local checks can also be removed; they are ignored by git through `*.db`.

## Known Limitations

- Having problem with Tavily
- Used DOCUMENT.md as the only file

With more time, I would add a hardened Tavily/search integration, MinerU-style PDF/layout parsing for richer multimodal document ingestion, task-aware model selection based on query complexity, better evidence ranking/deduplication, authentication for document operations, and concurrency controls for simultaneous proposal review, frontend.
