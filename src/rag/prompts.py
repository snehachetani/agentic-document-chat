from llama_index.core import PromptTemplate


QA_PROMPT = PromptTemplate(
    """
You are answering questions about the clouds document.

Rules:
- Use only the provided context.
- Do not use external knowledge.
- Do not call external tools.
- If the answer is not supported by the context, say so.
- Always mention the section ID or section IDs used.

Context:
{context_str}

Question:
{query_str}

Answer:
"""
)