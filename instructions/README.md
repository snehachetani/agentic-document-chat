# Take-home Assignment: Agentic Document Chat with Reviewable Updates

## Context

At AI4RA, we build workflows where users interact with structured regulatory documents, verify claims against evidence, and apply document changes through a controlled review process.

This assignment is a small, backend-focused version of that workflow. You will build an agentic chat system that lets a user ask questions about a short document, request section-level improvements, review proposed updates, and accept or reject those updates while preserving version history.

The goal is not to build a polished document editor. We want to understand your backend architecture, agent/tool workflow, document state model, citation handling, and practical engineering tradeoffs.

Expected completion time: around 2 days.

## Objective

Build a small backend application where a user can chat with a toy document about clouds.

The system should support:

1. Asking questions about the document or a specific section.
2. Summarizing a section.
3. Asking the system to improve, shorten, or rewrite a selected section.
4. Asking the system to verify a section using external evidence tools.
5. Creating a pending change proposal instead of directly overwriting document text.
6. Comparing, accepting, or rejecting a proposed change.
7. Preserving section version history.
8. Returning citations or evidence whenever external tools are used.

## Provided Materials

This folder includes:

- `clouds.pdf`: NASA, *Investigating the Climate System: CLOUDS and the Earth's Radiant Energy System*.
- `DOCUMENT.md`: the simplified section-based document your app should load.
- `TOOL_CONTRACTS.md`: required external evidence tools and suggested internal document operations.
- `SAMPLE_REQUESTS.md`: representative user requests and expected behavior.
- `EVALUATION.md`: how we will evaluate the submission.
- `OPTIONAL_STARTER_CODE/tools/`: optional Tavily-style search helpers plus LangChain `BaseTool` wrappers you may copy, modify, or replace.

Use `clouds.pdf` as background/source material for the assignment theme. Your app does not need to parse the full PDF unless you choose to. The canonical document content for this assignment is in `DOCUMENT.md`.

## What You Need To Build

Create a backend service, preferably with API routes that are easy to test from Swagger, curl, or Postman.

At minimum, the service should expose a way to:

- chat with the document
- list document sections and versions
- fetch a section
- create a change proposal
- compare a pending change with the current section text
- accept a change
- reject a change
- inspect version history

A basic frontend or simple chat UI is welcome but not required. Swagger/API docs, Postman-friendly endpoints, or a minimal CLI are enough if the backend behavior is clear.

You may use LangGraph, LangChain, OpenAI SDK, another agent framework, or your own orchestration code. We care more about clear design and controlled behavior than the specific framework.

## Required Behavior

### Document-only Q&A

For questions answerable from the document, the system should not call external search tools.

Expected flow:

```text
User question
-> identify relevant section
-> get section
-> answer from document
-> mention section ID
```

### Section summarization

For summarization requests, the system should use the selected section text and avoid external tools unless the user explicitly asks for outside evidence.

Expected flow:

```text
User asks to summarize section
-> get section
-> summarize
-> no external search unless explicitly requested
```

### Fact-checking and evidence lookup

For verification requests, the system should choose an appropriate evidence tool, return a concise fact-check summary, and include source evidence.

Expected flow:

```text
User asks to verify section
-> get section
-> decide which external tool is appropriate
-> call NASA/NOAA/general web search only if needed
-> compare retrieved evidence with section text
-> return fact-check summary with sources
```

### Proposed updates

The agent must not directly overwrite document text.

For any update, rewrite, improvement, or shortening request, the system must create a pending change proposal first.

Expected flow:

```text
User asks to update/rewrite section
-> get section
-> decide if external evidence is needed
-> call external tools only if needed
-> generate proposed text
-> create pending change proposal
-> return proposal summary and evidence used
```

A change proposal should use a shape similar to:

```json
{
  "change_id": "change_001",
  "section_id": "clouds_climate_change",
  "original_text": "...",
  "proposed_text": "...",
  "reason_for_change": "...",
  "evidence_used": [
    {
      "source_title": "...",
      "source_url": "...",
      "supporting_text": "..."
    }
  ],
  "status": "pending"
}
```

When a change is accepted:

- update the section text
- increment the section version
- preserve the old version in history
- mark the proposal as accepted

When a change is rejected:

- keep the section unchanged
- mark the proposal as rejected

## Important Constraints

- Do not build a full AI4RA product.
- Do not build a polished document editor.
- Do not overwrite section text without an explicit accept step.
- Do not call external tools for every request.
- Do not add unsupported factual claims to proposed text.
- Do not commit API keys.

Mocked evidence tools are acceptable. If you use real Tavily calls, load `TAVILY_API_KEY` from the environment.

## Suggested API Surface

You may design your own API, but a reasonable shape is:

```text
POST /chat
GET  /documents/{document_id}/sections
GET  /documents/{document_id}/sections/{section_id}
GET  /documents/{document_id}/sections/{section_id}/history
POST /documents/{document_id}/changes
GET  /documents/{document_id}/changes/{change_id}
GET  /documents/{document_id}/changes/{change_id}/compare
POST /documents/{document_id}/changes/{change_id}/accept
POST /documents/{document_id}/changes/{change_id}/reject
```

The `/chat` endpoint may call the same services internally, but the document operations should still be testable.

## Data Model Guidance

Use any persistence layer that is practical for a 2-day assignment:

- in-memory store
- SQLite
- JSON files
- Postgres
- another lightweight store

Your design should make it clear how you represent:

- document
- section
- current section version
- section version history
- change proposal
- evidence/citations
- tool trace or tool call log

## Expected Deliverables

Please submit:

1. GitHub repository or zip file.
2. Instructions to run the project locally.
3. Basic tests for the core document/change workflow.
4. Short architecture explanation in your README or a separate `ARCHITECTURE.md`.
5. Any assumptions and known limitations.
6. Optional screenshots or short demo video if you build a UI.

Your architecture explanation should cover:

- API/service boundaries
- agent orchestration approach
- tool selection logic
- document state and versioning model
- change proposal lifecycle
- citation/evidence handling
- limitations and what you would improve with more time

## Evaluation

We will evaluate the submission on:

- backend architecture and separation of concerns
- agentic design and tool selection
- controlled change management
- source grounding and citation traceability
- practicality and ease of local review

See `EVALUATION.md` for a more detailed rubric.
