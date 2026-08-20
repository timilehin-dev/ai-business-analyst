"""
Tests for the anti-hallucination layer:
  - deterministic grounding guard (numbers in report must exist in data)
  - code-execution path for calculations (model writes code, sandbox runs it)
"""
import json

import pytest

from agent.core.analyst import (
    find_ungrounded_numbers,
    grounding_node,
    code_generator_node,
    code_executor_node,
)
from agent.tools.sandbox import CodeSandboxTool


# ==================== GROUNDING GUARD ====================

class TestGroundingGuard:
    def test_exact_numbers_pass(self):
        data = {
            "columns": ["total_revenue", "top_category", "top_revenue"],
            "rows": [[697499.0, "infrastructure", 419400.0]],
            "row_count": 1,
            "truncated": False,
        }
        report = "Total revenue is 697,499.0. Top category is infrastructure with 419,400.0."
        assert find_ungrounded_numbers(report, data=data, confidence=0.9) == []

    def test_fabricated_total_detected(self):
        # The exact failure we saw live: model invented 700,490 instead of 697,499
        data = {
            "columns": ["total_revenue", "top_category", "top_revenue"],
            "rows": [[697499.0, "infrastructure", 419400.0]],
            "row_count": 1,
            "truncated": False,
        }
        report = "Total revenue is 700,490.0."
        ungrounded = find_ungrounded_numbers(report, data=data, confidence=0.9)
        assert 700490.0 in ungrounded
        assert 697499.0 not in ungrounded

    def test_confidence_percentage_allowed(self):
        # "90.0%" is the confidence level, not a hallucination
        data = {"columns": ["x"], "rows": [[10.0]], "row_count": 1, "truncated": False}
        report = "Confidence is 90.0%."
        assert find_ungrounded_numbers(report, data=data, confidence=0.9) == []

    def test_calendar_years_skipped(self):
        data = {"columns": ["x"], "rows": [[10.0]], "row_count": 1, "truncated": False}
        report = "Since 2024, revenue has grown."
        assert find_ungrounded_numbers(report, data=data, confidence=0.9) == []

    def test_dates_skipped(self):
        data = {"columns": ["x"], "rows": [[10.0]], "row_count": 1, "truncated": False}
        report = "Orders on 2023-05-12 and at 14:30 were counted."
        assert find_ungrounded_numbers(report, data=data, confidence=0.9) == []

    def test_computed_results_ground_reports(self):
        # Derived metrics from executed code are trusted
        data = {"columns": ["category", "revenue"], "rows": [["infra", 419400.0]], "row_count": 1, "truncated": False}
        computed = {"infra_share_pct": 60.1}
        report = "Infrastructure is 60.1% of revenue."
        assert find_ungrounded_numbers(report, data=data, computed=computed, confidence=0.9) == []

    def test_derived_percentage_without_code_is_flagged(self):
        # Model computed a percentage without code -> must be caught
        data = {"columns": ["category", "revenue"], "rows": [["infra", 419400.0]], "row_count": 1, "truncated": False}
        report = "Infrastructure is 60.1% of revenue."
        ungrounded = find_ungrounded_numbers(report, data=data, confidence=0.9)
        assert 60.1 in ungrounded

    def test_grounding_node_increments_count(self):
        state = {
            "final_response": "Total is 999999.0.",
            "execution_result": {"columns": ["x"], "rows": [[10.0]], "row_count": 1, "truncated": False},
            "computed_results": None,
            "confidence_score": 0.9,
            "sql_query": "SELECT 10 AS x",
            "grounding_count": 0,
        }
        out = grounding_node(state)
        assert out["grounding_errors"] == [999999.0]
        assert out["grounding_count"] == 1

    def test_grounding_node_clean_report(self):
        state = {
            "final_response": "The value is 10.0.",
            "execution_result": {"columns": ["x"], "rows": [[10.0]], "row_count": 1, "truncated": False},
            "computed_results": None,
            "confidence_score": 0.9,
            "sql_query": "SELECT 10 AS x",
            "grounding_count": 0,
        }
        out = grounding_node(state)
        assert out["grounding_errors"] == []
        assert out["grounding_count"] == 0


# ==================== CODE EXECUTION PATH ====================

class FakeModelRouter:
    """Returns a fixed code snippet for the code generator."""

    def __init__(self, code: str):
        self.code = code

    async def complete(self, messages, task_type="reasoning", **kwargs):
        return self.code


class TestCodeExecutionPath:
    @pytest.mark.asyncio
    async def test_code_generator_returns_code(self):
        router = FakeModelRouter("import json\nprint('RESULT:' + json.dumps({'total': 42}))")
        state = {
            "messages": [{"role": "user", "content": "What is the total?"}],
            "execution_result": {"columns": ["x"], "rows": [[42.0]], "row_count": 1, "truncated": False},
        }
        out = await code_generator_node(state, router)
        assert "RESULT" in out["python_code"]

    @pytest.mark.asyncio
    async def test_code_generator_strips_fences(self):
        router = FakeModelRouter("```python\nprint('RESULT:{\"a\": 1}')\n```")
        state = {
            "messages": [{"role": "user", "content": "q"}],
            "execution_result": {"columns": ["x"], "rows": [[1.0]], "row_count": 1, "truncated": False},
        }
        out = await code_generator_node(state, router)
        assert out["python_code"] == "print('RESULT:{\"a\": 1}')"

    @pytest.mark.asyncio
    async def test_code_executor_parses_result(self):
        sandbox = CodeSandboxTool(use_local_docker=False)
        code = (
            "import json, math\n"
            "data = {'rows': [[419400.0], [140249.0]]}\n"
            "total = sum(r[0] for r in data['rows'])\n"
            "share = round(419400.0 / total * 100, 2)\n"
            "print('RESULT:' + json.dumps({'total': total, 'share_pct': share}))"
        )
        state = {"python_code": code, "validation_errors": []}
        out = await code_executor_node(state, sandbox)
        assert out["computed_results"] == {"total": 559649.0, "share_pct": 74.94}
        assert out["validation_errors"] == []

    @pytest.mark.asyncio
    async def test_code_executor_reports_failure(self):
        sandbox = CodeSandboxTool(use_local_docker=False)
        state = {"python_code": "raise ValueError('boom')", "validation_errors": []}
        out = await code_executor_node(state, sandbox)
        assert out["computed_results"] is None
        assert any("no parseable RESULT" in e for e in out["validation_errors"])

    @pytest.mark.asyncio
    async def test_code_executor_no_code(self):
        sandbox = CodeSandboxTool(use_local_docker=False)
        state = {"python_code": "", "validation_errors": []}
        out = await code_executor_node(state, sandbox)
        assert out["computed_results"] is None
        assert any("No code generated" in e for e in out["validation_errors"])