"""
Tests for the learning loop: semantic/episodic/procedural memory, the
feedback -> rule promotion, and context assembly.
"""
import pytest

from agent.memory.context import AnalysisContext, build_context
from agent.memory.memory import (
    NEGATIVE_RATING_THRESHOLD,
    MemoryStore,
    memory_store,
)


@pytest.fixture
def store():
    """A fresh MemoryStore bound to the (already-isolated) test DB."""
    return memory_store


class TestSemanticMemory:
    def test_add_and_list_term(self, store):
        store.add_term("ARR", "Annual recurring revenue", source="user")
        terms = store.list_terms()
        assert any(t["term"] == "ARR" for t in terms)

    def test_add_updates_existing_term(self, store):
        store.add_term("ARR", "Annual recurring revenue")
        store.add_term("ARR", "Annualized run rate")
        terms = [t for t in store.list_terms() if t["term"] == "ARR"]
        assert len(terms) == 1
        assert terms[0]["definition"] == "Annualized run rate"

    def test_delete_term(self, store):
        store.add_term("MRR", "Monthly recurring revenue")
        term_id = next(t["id"] for t in store.list_terms() if t["term"] == "MRR")
        assert store.delete_term(term_id) is True
        assert store.delete_term(term_id) is False

    def test_relevant_terms_ranked_by_question(self, store):
        store.add_term("ARR", "Annual recurring revenue")
        store.add_term("churn", "Rate customers cancel a subscription")
        store.add_term("inventory", "Stock on hand in the warehouse")
        result = store.relevant_terms("how is our churn trending?")
        assert result and result[0]["term"] == "churn"


class TestProceduralMemory:
    def test_add_rule(self, store):
        rule = store.add_rule("Always exclude test accounts from revenue.")
        assert rule["active"] is True
        assert rule["rule"] == "Always exclude test accounts from revenue."

    def test_list_rules_active_only(self, store):
        store.add_rule("Rule A")
        store.add_rule("Rule B")
        store.add_rule("Rule B")  # duplicate: unique constraint keeps one row
        store.add_rule("Rule C")
        active = store.list_rules(active_only=True)
        assert len(active) >= 3

    def test_deactivate_rule(self, store):
        rule = store.add_rule("Rule to deactivate")
        assert store.deactivate_rule(rule["id"]) is True
        # Inactive rules drop out of the active-only list.
        assert all(r["rule"] != "Rule to deactivate" for r in store.list_rules(active_only=True))
        # A nonexistent rule reports nothing to deactivate.
        assert store.deactivate_rule(999999) is False


class TestFeedbackLoop:
    def test_feedback_promotes_correction_to_rule(self, store):
        episode_id = store.record_episode(
            "What is revenue?", "SELECT SUM(x) FROM orders", "100", 0.9
        )
        result = store.add_feedback(
            episode_id, rating=2, correction="Exclude refunded orders from revenue."
        )
        assert result["rule_created"] is True
        rules = [r["rule"] for r in store.list_rules(active_only=True)]
        assert "Exclude refunded orders from revenue." in rules

    def test_feedback_without_correction_creates_no_rule(self, store):
        episode_id = store.record_episode("What is revenue?")
        result = store.add_feedback(episode_id, rating=1, correction=None)
        assert result["rule_created"] is False

    def test_positive_feedback_creates_no_rule(self, store):
        episode_id = store.record_episode("What is revenue?")
        result = store.add_feedback(
            episode_id, rating=5, correction="Exclude refunded orders."
        )
        assert result["rule_created"] is False

    def test_feedback_unknown_episode_returns_none(self, store):
        assert store.add_feedback(999999, rating=3) is None

    def test_rejected_episode_not_recalled(self, store):
        store.record_episode("revenue by month")
        bad_id = store.record_episode("revenue by month for ACME")
        store.add_feedback(bad_id, rating=1, correction="wrong")
        similar = store.similar_episodes("revenue by month")
        # The badly-rated episode must be excluded from recall.
        assert all(e["id"] != bad_id for e in similar)


class TestContextAssembly:
    def test_build_context_includes_rules_and_glossary(self, store):
        store.add_term("ARR", "Annual recurring revenue")
        store.add_rule("Always exclude test accounts.")
        context = build_context("What is our ARR?", include_documents=False)

        assert "ARR" in context.to_metadata()["glossary_terms"]
        assert "Always exclude test accounts." in context.to_metadata()["rules_applied"]

    def test_prompt_renders_sections(self, store):
        store.add_term("ARR", "Annual recurring revenue")
        store.add_rule("Always exclude test accounts.")
        prompt = build_context("What is our ARR?", include_documents=False).to_prompt()
        assert "Business Glossary" in prompt
        assert "Standing Instructions" in prompt

    def test_empty_context_renders_empty_prompt(self, store):
        context = AnalysisContext()
        assert context.to_prompt() == ""
        assert context.to_metadata() == {
            "glossary_terms": [],
            "rules_applied": [],
            "similar_questions": [],
            "documents_used": [],
        }

    def test_user_context_prepended(self):
        prompt = AnalysisContext().to_prompt(user_context="We are a B2B SaaS company.")
        assert prompt.startswith("## Business Context")
        assert "B2B SaaS" in prompt


class TestAuditLog:
    def test_audit_and_list(self, store):
        store.audit("test.action", {"k": "v"}, actor="user")
        entries = store.list_audit(limit=10)
        assert any(e["action"] == "test.action" and e["actor"] == "user" for e in entries)

    def test_audit_filter_by_action(self, store):
        store.audit("filter.me")
        store.audit("other.action")
        entries = store.list_audit(action="filter.me")
        assert all(e["action"] == "filter.me" for e in entries)


class TestGlossaryFromSchema:
    def test_generate_glossary_from_schema(self, store, db_conn):
        added = store.generate_glossary_from_schema(db_conn)
        assert added > 0
        terms = {t["term"] for t in store.list_terms()}
        # Internal tables are skipped; business tables are captured.
        assert "orders" in terms or "customers" in terms or "products" in terms