"""
Tests for the SQL validator — the read-only guard for analyst-generated SQL.
"""
import pytest

from agent.tools.sql_validator import (
    SQLValidatorTool,
    blank_string_literals,
    split_statements,
    strip_sql_comments,
)


@pytest.fixture
def validator():
    return SQLValidatorTool(strict_mode=True)


class TestCommentStripping:
    def test_block_comment(self):
        assert "SELECT" in strip_sql_comments("/* intro */ SELECT 1").strip()

    def test_line_comment(self):
        assert strip_sql_comments("-- note\nSELECT 1").strip().startswith("SELECT")

    def test_comment_only_query_rejected(self, validator):
        ok, err = validator.validate("-- just a comment")
        assert not ok


class TestStringLiteralBlanking:
    def test_literal_content_blanked(self):
        masked = blank_string_literals("SELECT 'DROP the mic' FROM t")
        assert "DROP" not in masked.upper()

    def test_escaped_quote_handled(self):
        # The doubled quote ('' inside a literal) is masked along with the rest
        # of the literal content — it must not be mistaken for a closing quote.
        masked = blank_string_literals("SELECT 'it''s fine' FROM t")
        assert "fine" not in masked
        assert "FROM" in masked.upper()  # trailing part outside the literal survives

    def test_drop_inside_literal_not_flagged(self, validator):
        ok, err = validator.validate("SELECT 'DROP TABLE users' AS label")
        assert ok, err


class TestStatementSplitting:
    def test_single_statement(self):
        assert len(split_statements("SELECT 1")) == 1

    def test_multiple_statements(self):
        assert len(split_statements("SELECT 1; SELECT 2")) == 2

    def test_semicolon_inside_literal_ignored(self):
        assert len(split_statements("SELECT 'a;b' AS x")) == 1


class TestDangerousKeywords:
    def test_insert_blocked(self, validator):
        ok, err = validator.validate("INSERT INTO t VALUES (1)")
        assert not ok
        assert "INSERT" in err

    def test_drop_table_blocked(self, validator):
        ok, _ = validator.validate("DROP TABLE users")
        assert not ok

    def test_select_into_blocked(self, validator):
        ok, err = validator.validate("SELECT * INTO new_t FROM old_t")
        assert not ok
        assert "INTO" in err

    def test_multiple_statements_blocked(self, validator):
        ok, err = validator.validate("SELECT 1; DROP TABLE users")
        assert not ok

    def test_comment_prefixed_drop_blocked(self, validator):
        ok, _ = validator.validate("/* legit */ DROP TABLE users")
        assert not ok


class TestFunctionSafeKeywords:
    def test_replace_function_allowed(self, validator):
        ok, err = validator.validate("SELECT REPLACE(name, 'a', 'b') FROM t")
        assert ok, err

    def test_replace_into_blocked(self, validator):
        # "REPLACE INTO" is an upsert, not a function call.
        ok, _ = validator.validate("REPLACE INTO t VALUES (1)")
        assert not ok


class TestValidQueries:
    def test_simple_select(self, validator):
        ok, err = validator.validate("SELECT * FROM orders")
        assert ok, err

    def test_with_cte(self, validator):
        ok, err = validator.validate(
            "WITH c AS (SELECT 1 AS x) SELECT x FROM c"
        )
        assert ok, err

    def test_join_and_aggregate(self, validator):
        ok, err = validator.validate(
            "SELECT c.name, SUM(o.amount) AS revenue "
            "FROM orders o JOIN customers c ON c.id = o.customer_id "
            "GROUP BY c.name"
        )
        assert ok, err

    def test_empty_query(self, validator):
        ok, err = validator.validate("")
        assert not ok
        assert err

    def test_suggest_fix_mentions_select_only(self, validator):
        prompt = validator.suggest_fix("DROP t", "Dangerous operation")
        assert "SELECT-only" in prompt