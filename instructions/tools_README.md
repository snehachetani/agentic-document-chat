# Optional Starter Tools

This folder contains optional evidence tools for candidates.

There are two layers:

- `search_client.py`: framework-neutral Tavily/mock functions that return the contracts in `TOOL_CONTRACTS.md`.
- `*_tool.py`: LangChain `BaseTool` wrappers with Pydantic input schemas, similar to AI4RA's production tool style.

Use `tools.py` as a small registry when wiring an agent:

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from tools import build_langchain_tools

llm = ChatOpenAI(model="gpt-4o-mini")
agent = create_react_agent(llm, build_langchain_tools())
```

Candidates may also skip LangChain entirely and call the plain functions from `search_client.py` inside their own service/orchestrator.


## Setup With uv

This starter folder includes a `pyproject.toml` so candidates can create an isolated environment quickly.

From this directory:

```bash
cd take-home-assigment-agentic-tooling/OPTIONAL_STARTER_CODE/tools
uv sync
```

Verify the tools import:

```bash
uv run python -c "from tools import build_langchain_tools; print([tool.name for tool in build_langchain_tools()])"
```

Run with real Tavily search by setting:

```bash
export TAVILY_API_KEY=...
```

Without `TAVILY_API_KEY`, the tools return deterministic mock results so the backend workflow can be developed and tested offline.

The internal document operations, such as `get_section`, `create_change_proposal`, `accept_change`, and `reject_change`, should be implemented by the candidate's backend service. They are intentionally not included here as ready-made tools.
