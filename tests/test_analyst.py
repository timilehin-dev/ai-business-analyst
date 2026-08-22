"""
Graph-level tests: full analysis flow, self-correction retry, and
termination when no database is configured.
"""
import pytest

from conftest import FakeModelRouter, build_graph, PLAN_JSON


class TestFullFlow:
    @pytest.mark.asyncio
    async def test_happy_path(self, happy_router, sample_db_path):
        graph = build_graph(happy_router, database_url=f"sqlite:///{sample_db_path}")
        result = await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": "Who are our top customers?"}],
                "business_context": "SaaS company",
                "market_context": "",
                "schema_info": "",
                "plan": "",
                "search_queries": [],
                "sql_query": None,
                "python_code": None,
                "execution_result": None,
                "validation_errors": [],
                "analysis_draft": "",
                "final_response": "",
                "confidence_score": 0.0,
                "needs_human_escalation": False,
                "iteration_count": 0,
                "max_iterations": 3,
            }
        )

        assert "Revenue by customer is healthy" in result["final_response"]
        assert result["confidence_score"] > 0.5
        assert result["needs_human_escalation"] is False
        assert result["execution_result"]["row_count"] == 2
        assert "SELECT" in result["sql_query"]
        # planner + sql_generator + reporter = 3 reasoning/sql calls
        assert happy_router.calls.count("reasoning") == 2
        assert happy_router.calls.count("sql") == 1

    @pytest.mark.asyncio
    async def test_schema_info_auto_crawled(self, happy_router, sample_db_path):
        """analyze() should crawl the schema when none is provided."""
        from agent.core.analyst import AutonomousAnalyst

        analyst = AutonomousAnalyst(
            {"reasoning": "fake", "sql": "fake"},
            newsroom_enabled=False,
            database_url=f"sqlite:///{sample_db_path}",
        )
        # Inject the fake router into the already-built graph's closures
        # by rebuilding via create_agent_graph with the fake router.
        analyst.graph = build_graph(happy_router, database_url=f"sqlite:///{sample_db_path}")

        schema = analyst.get_schema()
        assert "TABLE customers" in schema

        result = await analyst.analyze("Who are our top customers?")
        assert result["answer"]
        assert result["data"]["row_count"] == 2


class TestSelfCorrection:
    @pytest.mark.asyncio
    async def test_retry_after_security_violation(self, sample_db_path):
        """A blocked (non-SELECT) query must trigger a retry with a valid query."""
        router = FakeModelRouter(
            {
                "reasoning": [
                    PLAN_JSON,
                    "## Report\nRecovered after retry.",
                ],
                "sql": [
                    "DELETE FROM customers",  # blocked by validator
                    "SELECT COUNT(*) AS n FROM customers",
                ],
            }
        )
        graph = build_graph(router, database_url=f"sqlite:///{sample_db_path}")
        result = await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": "How many customers?"}],
                "business_context": "",
                "market_context": "",
                "schema_info": "",
                "plan": "",
                "search_queries": [],
                "sql_query": None,
                "python_code": None,
                "execution_result": None,
                "validation_errors": [],
                "analysis_draft": "",
                "final_response": "",
                "confidence_score": 0.0,
                "needs_human_escalation": False,
                "iteration_count": 0,
                "max_iterations": 3,
            }
        )

        assert "Recovered after retry" in result["final_response"]
        assert result["sql_query"] == "SELECT COUNT(*) AS n FROM customers"
        assert result["execution_result"]["rows"] == [[2]]
        assert router.calls.count("sql") == 2  # one failed attempt + one retry

    @pytest.mark.asyncio
    async def test_loop_terminates_without_database(self):
        """No DB configured: retries exhaust, then escalate (no infinite loop)."""
        router = FakeModelRouter(
            {
                "reasoning": [PLAN_JSON, "## Report\nShould not be reached."],
                "sql": ["SELECT COUNT(*) FROM customers"],
            }
        )
        graph = build_graph(router, database_url=None)
        result = await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": "How many customers?"}],
                "business_context": "",
                "market_context": "",
                "schema_info": "",
                "plan": "",
                "search_queries": [],
                "sql_query": None,
                "python_code": None,
                "execution_result": None,
                "validation_errors": [],
                "analysis_draft": "",
                "final_response": "",
                "confidence_score": 0.0,
                "needs_human_escalation": False,
                "iteration_count": 0,
                "max_iterations": 3,
            }
        )

        # initial attempt + 2 retries = 3 sql_generator calls, then escalate
        assert router.calls.count("sql") == 3
        assert result["needs_human_escalation"] is True
        assert result["confidence_score"] == 0.0
        assert result["final_response"] == ""