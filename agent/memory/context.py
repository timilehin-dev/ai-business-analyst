"""
Context assembly.

Turns the question plus everything the analyst remembers into the prompt
blocks the graph nodes consume. Retrieval is used rather than dumping the
whole corpus, so context stays inside the model's window and signal is not
diluted by irrelevant documents.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.memory.memory import memory_store
from agent.memory.retrieval import score_documents, snippet

MAX_DOC_CHARS = 1200
MAX_DOCS = 4
MAX_EPISODES = 3
MAX_TERMS = 5
MAX_RULES = 10


@dataclass
class AnalysisContext:
    """Retrieved context for one question."""

    glossary: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    episodes: List[Dict[str, Any]] = field(default_factory=list)
    documents: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def rule_ids(self) -> List[int]:
        return [r["id"] for r in self.rules]

    def to_prompt(self, user_context: str = "") -> str:
        """Render as a prompt block. Empty string when nothing is remembered."""
        sections: List[str] = []

        if user_context and user_context.strip():
            sections.append(f"## Business Context\n{user_context.strip()}")

        if self.glossary:
            lines = [f"- **{t['term']}**: {t['definition']}" for t in self.glossary]
            sections.append("## Business Glossary (how this organization defines things)\n" + "\n".join(lines))

        if self.rules:
            lines = [f"- {r['rule']}" for r in self.rules]
            sections.append(
                "## Standing Instructions (learned from prior corrections — follow these)\n"
                + "\n".join(lines)
            )

        if self.episodes:
            lines = []
            for e in self.episodes:
                lines.append(f"- Q: {e['question']}")
                if e.get("sql_query"):
                    lines.append(f"  SQL used: {e['sql_query']}")
            sections.append(
                "## Similar Past Analyses (reuse the approach where it fits)\n" + "\n".join(lines)
            )

        if self.documents:
            blocks = [
                f"### [{d['source']}] {d['title']}\n{d['excerpt']}" for d in self.documents
            ]
            sections.append(
                "## Relevant Documents (uploaded files, Drive, Sheets, email)\n"
                + "\n\n".join(blocks)
            )

        return "\n\n".join(sections)

    def to_metadata(self) -> Dict[str, Any]:
        """Compact provenance summary for API responses and the UI."""
        return {
            "glossary_terms": [t["term"] for t in self.glossary],
            "rules_applied": [r["rule"] for r in self.rules],
            "similar_questions": [e["question"] for e in self.episodes],
            "documents_used": [
                {"source": d["source"], "title": d["title"]} for d in self.documents
            ],
        }


def _retrieve_documents(question: str, limit: int = MAX_DOCS) -> List[Dict[str, Any]]:
    """Rank the ingested knowledge graph against the question."""
    try:
        from agent.connectors.storage import document_store

        docs = document_store.list_documents(limit=300)
    except Exception:
        return []

    if not docs:
        return []

    ranked = score_documents(
        question, docs, key=lambda d: f"{d['title']} {d['content'][:4000]}", limit=limit
    )
    return [
        {
            "id": d["id"],
            "source": d["source"],
            "title": d["title"],
            "excerpt": snippet(d["content"], question, MAX_DOC_CHARS),
            "score": round(score, 3),
        }
        for d, score in ranked
    ]


def build_context(
    question: str,
    user_context: str = "",
    include_documents: bool = True,
) -> AnalysisContext:
    """
    Gather glossary, standing rules, similar past analyses, and relevant
    documents for a question.

    Rules are always included (they are instructions, not recall); everything
    else is retrieved by relevance.
    """
    context = AnalysisContext()

    try:
        context.glossary = memory_store.relevant_terms(question, limit=MAX_TERMS)
    except Exception:
        context.glossary = []

    try:
        context.rules = memory_store.list_rules(active_only=True, limit=MAX_RULES)
    except Exception:
        context.rules = []

    try:
        context.episodes = memory_store.similar_episodes(question, limit=MAX_EPISODES)
    except Exception:
        context.episodes = []

    if include_documents:
        context.documents = _retrieve_documents(question)

    return context
