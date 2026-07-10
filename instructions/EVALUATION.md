# Evaluation Criteria

We are looking for a practical 2-day backend assignment, not a production system.

## Backend Architecture

Strong submissions will show:

- clean separation between APIs, agent orchestration, tools, document store, and versioning
- sensible data models for sections, changes, evidence, and history
- maintainable code structure
- clear error handling for missing sections, invalid change states, and failed tools
- APIs or commands that are easy to run locally

## Agentic Design

Strong submissions will show:

- appropriate tool selection based on user intent
- no unnecessary external tool calls for document-only requests
- clear tool traces or logs that explain what the agent did
- explicit distinction between document Q&A, summarization, verification, and update requests
- controlled behavior when the user asks for unsupported or ambiguous actions

## Change Management

Strong submissions will show:

- all edits go through pending change proposals
- accept/reject behavior is deterministic and testable
- accepted changes increment section versions
- old section versions remain inspectable
- rejected changes do not mutate section content
- repeated accept/reject attempts are handled safely

## Source Grounding

Strong submissions will show:

- external claims include source evidence
- evidence includes source title, URL, and supporting text
- proposed changes distinguish original document content from external sources
- the system avoids unsupported factual additions
- mocked tools, if used, return realistic and traceable evidence

## Practicality

Strong submissions will show:

- the project can be run locally with clear instructions
- core behavior is covered by basic tests
- the implementation is simple enough to review quickly
- the candidate clearly documents assumptions and limitations
- the design is realistic but not overbuilt

## Suggested Rubric

| Area | Weight |
| --- | ---: |
| Backend architecture | 25% |
| Agent/tool workflow | 25% |
| Change proposal and version history | 25% |
| Evidence/citation traceability | 15% |
| Tests, docs, and local usability | 10% |

## Bonus Credit

Optional strengths:

- simple UI or chat interface
- readable visual diff for proposed updates
- persistent storage beyond in-memory state
- evaluation script for sample requests
- streaming chat responses
- careful handling of concurrent updates
