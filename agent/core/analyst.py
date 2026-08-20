"""
Core Agent Logic using LangGraph.
Implements the Plan → Search → Query → Validate → Report workflow.
Integrates Newsroom, Code Sandbox, SQL Validator, and real database execution.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator
import json
import asyncio
import functools

from agent.models.provider import ModelRouter
from agent.tools.newsroom import NewsroomTool
from agent.tools.sandbox import CodeSandboxTool
from agent.tools.sql_validator import SQLValidatorTool
from agent.tools.database import DatabaseConnection
from api.config import settings


# ==================== STATE DEFINITION ====================

class AgentState(TypedDict):
    """Complete state representation for the agent."""
    
    # Input & Context
    messages: Annotated[List[Dict[str, str]], operator.add]
    business_context: str
    market_context: str
    schema_info: str

    # Analysis Components
    plan: str
    search_queries: List[str]
    sql_query: Optional[str]
    python_code: Optional[str]  # For code sandbox execution
    execution_result: Optional[Any]
    computed_results: Optional[Any]  # Exact numbers from executed code
    validation_errors: List[str]
    grounding_errors: List[str]  # Numbers in report not found in data
    grounding_count: int  # Bounded regeneration attempts

    # Output
    analysis_draft: str
    final_response: str
    confidence_score: float
    needs_human_escalation: bool

    # Metadata
    iteration_count: int
    max_iterations: int


# ==================== NODE FUNCTIONS ====================

async def planner_node(state: AgentState, model_router: ModelRouter) -> AgentState:
    """
    Analyze the user's question and create an analysis plan.
    Determines if external search or code execution is needed.
    """
    messages = state['messages']
    last_message = messages[-1]['content'] if messages else ""
    
    system_prompt = """You are a strategic business analyst planner.
Your job is to:
1. Understand the user's question
2. Identify what internal data is needed
3. Determine if external market context would help (Newsroom)
4. Decide if complex calculations require Python code (Sandbox)
5. Create a step-by-step analysis plan

If the question involves market trends, competitors, industry benchmarks, 
or recent events, generate search queries for the Newsroom module.

If the question requires complex statistics, forecasting, or custom calculations,
flag that Python code execution is needed.

Return JSON with this structure:
{
    "plan": "Step-by-step analysis approach",
    "needs_external_search": true/false,
    "search_queries": ["query1", "query2"] (if needed),
    "needs_code_execution": true/false,
    "required_tables": ["table1", "table2"],
    "metrics_needed": ["metric1", "metric2"]
}
"""
    
    response = await model_router.complete(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Business context: {state.get('business_context', 'N/A')}\n\nQuestion: {last_message}"}
        ],
        task_type='reasoning',
        temperature=0.3
    )
    
    # Parse response
    try:
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            plan_data = json.loads(response[json_start:json_end])
        else:
            plan_data = {
                "plan": response,
                "needs_external_search": False,
                "search_queries": [],
                "needs_code_execution": False,
                "required_tables": [],
                "metrics_needed": []
            }
    except:
        plan_data = {
            "plan": response,
            "needs_external_search": False,
            "search_queries": [],
            "needs_code_execution": False,
            "required_tables": [],
            "metrics_needed": []
        }
    
    return {
        'plan': plan_data.get('plan', ''),
        'search_queries': plan_data.get('search_queries', []),
        'needs_code_execution': plan_data.get('needs_code_execution', False),
        'business_context': state.get('business_context', '')
    }


async def newsroom_node(state: AgentState, newsroom_tool: NewsroomTool) -> AgentState:
    """
    Fetch external market intelligence if needed.
    """
    search_queries = state.get('search_queries', [])
    
    if not search_queries:
        return {'market_context': 'No external search required.'}
    
    results = []
    for query in search_queries:
        result = await newsroom_tool.search(query, topic="market intelligence")
        results.append(result)
    
    market_context = "\n\n".join(results)
    return {'market_context': market_context}


async def sql_generator_node(state: AgentState, model_router: ModelRouter) -> AgentState:
    """
    Generate SQL query based on plan and schema.
    Includes previous execution errors so the agent can self-correct.
    """
    plan = state.get('plan', '')
    schema_info = state.get('schema_info', '')
    messages = state['messages']
    last_message = messages[-1]['content']
    previous_errors = state.get('validation_errors', [])
    
    system_prompt = f"""You are an expert SQL generator.
Given the database schema and analysis plan, write a precise SQL query.

SCHEMA:
{schema_info}

RULES:
- Only use SELECT statements (read-only)
- Use appropriate JOINs based on relationships
- Include comments explaining each part
- Optimize for performance
- Return ONLY the SQL query, no explanations

ANALYSIS PLAN:
{plan}
"""
    if previous_errors:
        system_prompt += f"""
PREVIOUS ATTEMPT FAILED. These errors were reported — fix them in your new query:
{chr(10).join(previous_errors)}
"""
    
    response = await model_router.complete(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate SQL for: {last_message}"}
        ],
        task_type='sql',
        temperature=0.1
    )
    
    # Extract SQL from response
    sql_query = response.strip()
    if "```sql" in sql_query:
        sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
    elif "```" in sql_query:
        sql_query = sql_query.split("```")[1].split("```")[0].strip()
    
    return {'sql_query': sql_query}


async def executor_node(
    state: AgentState,
    sql_validator: SQLValidatorTool,
    db_conn: Optional[DatabaseConnection] = None
) -> AgentState:
    """
    Execute the SQL query against the real database with validation.
    Falls back to a clear error when no database is configured.
    """
    sql_query = state.get('sql_query', '')
    iteration = state.get('iteration_count', 0) + 1
    
    if not sql_query:
        return {
            'execution_result': None,
            'validation_errors': ['No SQL query generated'],
            'iteration_count': iteration
        }
    
    # SECURITY: Validate SQL is read-only using validator tool
    is_valid, error_msg = sql_validator.validate(sql_query)
    if not is_valid:
        return {
            'execution_result': None,
            'validation_errors': [f'Security violation: {error_msg}'],
            'iteration_count': iteration
        }
    
    if db_conn is None:
        return {
            'execution_result': None,
            'validation_errors': ['Database not configured. Complete the setup wizard first.'],
            'iteration_count': iteration
        }
    
    # Execute against the real database (read-only enforced in the connection layer)
    try:
        execution_result = db_conn.execute_readonly(sql_query)
        return {
            'execution_result': execution_result,
            'validation_errors': [],
            'iteration_count': iteration
        }
    except Exception as e:
        return {
            'execution_result': None,
            'validation_errors': [f'Execution failed: {str(e)}'],
            'iteration_count': iteration
        }


async def validator_node(state: AgentState, model_router: ModelRouter) -> AgentState:
    """
    Validate results for statistical soundness and logical consistency.
    """
    execution_result = state.get('execution_result')
    validation_errors = state.get('validation_errors', [])
    
    if not execution_result or validation_errors:
        return {
            'confidence_score': 0.0,
            'needs_human_escalation': True
        }
    
# Check data quality
    row_count = execution_result.get('row_count', 0)
    truncated = execution_result.get('truncated', False)
    errors = list(validation_errors)
    
    if row_count == 0:
        errors.append('No data returned from query')
        confidence = 0.3
    else:
        # Query executed and returned data: high base confidence.
        # Row count does NOT drive trust — a 2-row answer can be exact.
        confidence = 0.9
    
    # Penalize truncated results (query exceeded the row limit, aggregates may be safer)
    if truncated:
        confidence -= 0.2
        errors.append('Result truncated: query exceeded the row limit, aggregates may be safer')
    
    confidence = max(0.0, min(1.0, confidence))
    escalation = confidence < 0.6 or row_count == 0
    
    return {
        'confidence_score': confidence,
        'needs_human_escalation': escalation,
        'validation_errors': errors
    }


async def reporter_node(state: AgentState, model_router: ModelRouter) -> AgentState:
    """
    Synthesize findings into a comprehensive report.
    Combines internal data, external context, and confidence levels.
    """
    messages = state['messages']
    last_message = messages[-1]['content']
    execution_result = state.get('execution_result')
    computed_results = state.get('computed_results')
    market_context = state.get('market_context', '')
    confidence = state.get('confidence_score', 0.5)
    validation_errors = state.get('validation_errors', [])
    grounding_errors = state.get('grounding_errors', [])

    system_prompt = f"""You are a senior business analyst preparing a report.

CONTEXT:
- User Question: {last_message}
- Market Intelligence: {market_context[:500] if market_context else 'None'}
- Confidence Level: {confidence:.1%}
- Validation Issues: {', '.join(validation_errors) if validation_errors else 'None'}

DATA RESULTS (SQL output):
{json.dumps(execution_result, default=str) if execution_result else 'No data'}

COMPUTED RESULTS (exact, from executed code — trust these completely):
{json.dumps(computed_results, default=str) if computed_results else 'None'}

GUIDELINES:
1. Start with a clear executive summary
2. Present key findings with supporting numbers
3. If market context exists, integrate it naturally
4. Be transparent about confidence levels and limitations
5. Provide actionable recommendations
6. If confidence is low or issues exist, clearly state them
7. CRITICAL: Never compute, sum, derive, or convert numbers yourself.
   Quote figures EXACTLY as they appear in DATA RESULTS or COMPUTED RESULTS.
   If a figure is not in the data, do not invent it — say the breakdown instead.
   LLM arithmetic is unreliable; every number you write must exist verbatim
   in the data above.

FORMAT:
Use markdown with clear sections, bullet points, and bold text for emphasis.
"""

    if grounding_errors:
        system_prompt += f"""
GROUNDING CHECK FAILED — your previous report contained numbers that do not
appear in the data: {grounding_errors}
Rewrite the report using ONLY numbers from DATA RESULTS and COMPUTED RESULTS.
Remove or rephrase every figure that is not in the data. Do not recompute anything.
"""
    
    response = await model_router.complete(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the final analysis report."}
        ],
        task_type='reasoning',
        temperature=0.5
    )
    
    return {
        'final_response': response,
        'analysis_draft': response
    }


async def code_generator_node(state: AgentState, model_router: ModelRouter) -> AgentState:
    """
    Write Python code that computes derived metrics from the SQL results.

    The model NEVER computes numbers itself — it writes code that does.
    The code embeds the SQL results as a literal and prints a single
    RESULT:<json> line, which the executor parses as exact numbers.
    """
    execution_result = state.get('execution_result')
    question = state['messages'][-1]['content']

    system_prompt = f"""You are a senior data analyst. The SQL query returned these results:

{json.dumps(execution_result, default=str) if execution_result else 'No data'}

The user's question requires calculations beyond what the SQL returned
(percentages, growth rates, statistics, forecasts, comparisons, ...).

Write Python code that:
1. Embeds the data above directly in the code as a Python literal
2. Computes every derived metric needed to answer: {question}
3. Prints exactly one line at the end: RESULT:{{json}} where json is a
   JSON object of the computed values (numbers only, rounded to 2 decimals)

RULES:
- Use ONLY the stdlib modules math, statistics, json (they are available)
- No network, no file access, no other imports
- The code must run standalone (data embedded, no external input)
- Print ONLY the RESULT line — no other output

Write ONLY the code, no explanations:"""

    response = await model_router.complete(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write the calculation code for: {question}"}
        ],
        task_type='reasoning',
        temperature=0.1
    )

    code = response.strip()
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()

    return {'python_code': code}


async def code_executor_node(state: AgentState, sandbox: CodeSandboxTool) -> AgentState:
    """
    Execute the generated code in the sandbox and parse the RESULT line.
    Only executed output becomes computed_results — never model tokens.
    """
    code = state.get('python_code', '')
    if not code:
        return {
            'computed_results': None,
            'validation_errors': state.get('validation_errors', []) + ['No code generated for calculation'],
        }

    result = await sandbox.execute(code)
    computed = None
    if result.get('success'):
        for line in (result.get('output') or '').splitlines():
            if line.startswith('RESULT:'):
                try:
                    computed = json.loads(line[len('RESULT:'):].strip())
                except json.JSONDecodeError:
                    continue
                break

    errors = list(state.get('validation_errors', []))
    if computed is None:
        errors.append(f'Code execution produced no parseable RESULT: {result.get("error") or result.get("output", "")[:200]}')

    return {
        'computed_results': computed,
        'validation_errors': errors,
    }


def grounding_node(state: AgentState) -> AgentState:
    """
    DETERMINISTIC guard (no LLM): every number in the report must appear
    in the data (SQL results, computed results, confidence). Any number
    the model invented is flagged so the reporter can regenerate.
    """
    report = state.get('final_response', '')
    ungrounded = find_ungrounded_numbers(
        report,
        data=state.get('execution_result'),
        computed=state.get('computed_results'),
        confidence=state.get('confidence_score', 0.0),
        sql=state.get('sql_query', ''),
    )
    return {
        'grounding_errors': ungrounded,
        'grounding_count': state.get('grounding_count', 0) + (1 if ungrounded else 0),
    }


# ==================== GROUNDING (DETERMINISTIC NUMBER CHECK) ====================

import re as _re

_NUM_RE = _re.compile(r'-?\d[\d,]*(?:\.\d+)?')
_DATE_RE = _re.compile(
    r'\d{4}-\d{1,2}-\d{1,2}|\d{1,2}:\d{2}(?::\d{2})?|\d{1,2}/\d{1,2}/\d{4}'
)


def _extract_numbers(text: str) -> List[float]:
    """All numeric quantities in text, skipping date/time tokens."""
    text = _DATE_RE.sub(' ', text or '')
    out = []
    for m in _NUM_RE.finditer(text):
        s = m.group().replace(',', '')
        try:
            out.append(float(s))
        except ValueError:
            continue
    return out


def _collect_allowed_numbers(data, computed, confidence: float, sql: str) -> set:
    """Every number that legitimately appears in the analysis data."""
    allowed = set()

    def add(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            allowed.add(float(v))
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)
        elif isinstance(v, dict):
            for x in v.values():
                add(x)

    add(data)
    add(computed)
    allowed.add(float(confidence))
    allowed.add(round(confidence * 100, 2))  # "90.0%" form
    for n in _extract_numbers(sql):  # numbers the model may quote from the query
        allowed.add(n)
    return allowed


def find_ungrounded_numbers(
    report: str,
    data=None,
    computed=None,
    confidence: float = 0.0,
    sql: str = '',
) -> List[float]:
    """Return numbers in the report that do not exist in the data."""
    allowed = _collect_allowed_numbers(data, computed, confidence, sql)
    ungrounded = []
    for n in _extract_numbers(report):
        # Skip calendar years (dates are not arithmetic claims).
        if n.is_integer() and 1900 <= n <= 2100:
            continue
        if n not in allowed:
            ungrounded.append(n)
    return ungrounded


# ==================== GRAPH CONSTRUCTION ====================

def create_agent_graph(
    model_router: ModelRouter, 
    newsroom_tool: NewsroomTool,
    sql_validator: SQLValidatorTool,
    db_conn: Optional[DatabaseConnection] = None
) -> StateGraph:
    """
    Build the LangGraph state machine for the autonomous analyst.
    Integrates Newsroom, Code Sandbox, SQL validation, and real database execution.
    """
    
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes with bound dependencies.
    # NOTE: use functools.partial, NOT lambdas — a lambda returning a coroutine
    # is treated as a sync node by langgraph and never awaited.
    workflow.add_node("planner", functools.partial(planner_node, model_router=model_router))
    workflow.add_node("newsroom", functools.partial(newsroom_node, newsroom_tool=newsroom_tool))
    workflow.add_node("sql_generator", functools.partial(sql_generator_node, model_router=model_router))
    workflow.add_node("executor", functools.partial(executor_node, sql_validator=sql_validator, db_conn=db_conn))
    workflow.add_node("validator", functools.partial(validator_node, model_router=model_router))
    workflow.add_node("code_generator", functools.partial(code_generator_node, model_router=model_router))
    workflow.add_node("code_executor", functools.partial(code_executor_node, sandbox=CodeSandboxTool()))
    workflow.add_node("reporter", functools.partial(reporter_node, model_router=model_router))
    workflow.add_node("grounding", grounding_node)
    
    # Define edges
    workflow.set_entry_point("planner")
    
    # Planner → conditional branch to newsroom or directly to SQL
    def route_after_planner(state: AgentState) -> str:
        if state.get('search_queries', []):
            return "newsroom"
        return "sql_generator"
    
    workflow.add_conditional_edges(
        source="planner",
        path=route_after_planner,
        path_map={
            "newsroom": "newsroom",
            "sql_generator": "sql_generator"
        }
    )
    
    # Newsroom → SQL Generator
    workflow.add_edge("newsroom", "sql_generator")
    
    # SQL Generator → Executor
    workflow.add_edge("sql_generator", "executor")
    
    # Executor → Validator, or retry SQL generation on failure (self-correction)
    def route_after_executor(state: AgentState) -> str:
        if state.get('validation_errors') and state.get('iteration_count', 0) < state.get('max_iterations', 3):
            return "retry"
        return "validator"
    
    workflow.add_conditional_edges(
        source="executor",
        path=route_after_executor,
        path_map={
            "retry": "sql_generator",
            "validator": "validator"
        }
    )
    
    # Validator → code path (calculations) or reporter, or escalate
    def route_after_validator(state: AgentState) -> str:
        if state.get('needs_human_escalation', False):
            return "escalate"
        if state.get('needs_code_execution', False):
            return "code_generator"
        return "reporter"

    workflow.add_conditional_edges(
        source="validator",
        path=route_after_validator,
        path_map={
            "reporter": "reporter",
            "code_generator": "code_generator",
            "escalate": END  # Could add escalation node later
        }
    )

    # Code path: generate → execute → report
    workflow.add_edge("code_generator", "code_executor")
    workflow.add_edge("code_executor", "reporter")

    # Reporter → Grounding (deterministic number check)
    workflow.add_edge("reporter", "grounding")

    # Grounding → regenerate report (bounded) or end
    def route_after_grounding(state: AgentState) -> str:
        if state.get('grounding_errors') and state.get('grounding_count', 0) < 2:
            return "reporter"
        return "end"

    workflow.add_conditional_edges(
        source="grounding",
        path=route_after_grounding,
        path_map={
            "reporter": "reporter",
            "end": END,
        }
    )

    return workflow.compile()


# ==================== MAIN AGENT CLASS ====================

class AutonomousAnalyst:
    """
    Main agent class that orchestrates the entire analysis workflow.
    Integrates Newsroom, Code Sandbox, SQL Validation, and real database execution.
    """
    
    def __init__(
        self,
        model_config: Dict[str, str],
        newsroom_enabled: bool = True,
        database_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.model_router = ModelRouter(model_config, api_key=api_key, api_base=api_base)
        self.newsroom_tool = NewsroomTool(enabled=newsroom_enabled)
        self.sql_validator = SQLValidatorTool(strict_mode=True)
        self.database_url = database_url
        self.db_conn: Optional[DatabaseConnection] = None
        if database_url:
            self.db_conn = DatabaseConnection(database_url)
        self.graph = create_agent_graph(
            self.model_router, 
            self.newsroom_tool, 
            self.sql_validator,
            self.db_conn
        )
    
    def get_schema(self) -> str:
        """Return the crawled schema for the configured database (or a hint to set one up)."""
        if self.db_conn is None:
            return "No database configured. Complete the setup wizard to connect one."
        return self.db_conn.crawl_schema()
    
    async def analyze(self, question: str, context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Run complete analysis workflow for a given question.
        
        Args:
            question: Natural language business question
            context: Optional context dict with 'business_context', 'schema_info'
            
        Returns:
            Dict with final_response, confidence_score, and metadata
        """
        schema_info = (context.get('schema_info') if context and context.get('schema_info')
                       else self.get_schema())
        
        initial_state = {
            'messages': [{'role': 'user', 'content': question}],
            'business_context': context.get('business_context', '') if context else '',
            'market_context': '',
            'schema_info': schema_info,
            'plan': '',
            'search_queries': [],
            'sql_query': None,
            'python_code': None,
            'execution_result': None,
            'computed_results': None,
            'validation_errors': [],
            'grounding_errors': [],
            'grounding_count': 0,
            'analysis_draft': '',
            'final_response': '',
            'confidence_score': 0.0,
            'needs_human_escalation': False,
            'needs_code_execution': False,
            'iteration_count': 0,
            'max_iterations': 3
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            'answer': result['final_response'],
            'confidence': result['confidence_score'],
            'sql': result.get('sql_query'),
            'data': result.get('execution_result'),
            'computed': result.get('computed_results'),
            'market_context': result.get('market_context'),
            'needs_review': result.get('needs_human_escalation', False)
        }


# Factory function
def create_analyst(
    config: Dict[str, str],
    newsroom_enabled: bool = True,
    database_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> AutonomousAnalyst:
    """Create configured analyst instance."""
    return AutonomousAnalyst(
        config, newsroom_enabled, database_url, api_key, api_base
    )
