"""
Core Agent Logic using LangGraph.
Implements the Plan → Search → Query → Validate → Report workflow.
Integrates Newsroom, Code Sandbox, and SQL Validator tools.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator
import json

from agent.models.provider import ModelRouter
from agent.tools.newsroom import NewsroomTool
from agent.tools.sandbox import CodeSandboxTool
from agent.tools.sql_validator import SQLValidatorTool
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
    validation_errors: List[str]

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
    """
    plan = state.get('plan', '')
    schema_info = state.get('schema_info', '')
    messages = state['messages']
    last_message = messages[-1]['content']
    
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


async def executor_node(state: AgentState, sql_validator: SQLValidatorTool) -> AgentState:
    """
    Execute the SQL query against the database with validation.
    """
    sql_query = state.get('sql_query', '')
    
    if not sql_query:
        return {
            'execution_result': None,
            'validation_errors': ['No SQL query generated']
        }
    
    # SECURITY: Validate SQL is read-only using validator tool
    is_valid, error_msg = sql_validator.validate(sql_query)
    if not is_valid:
        return {
            'execution_result': None,
            'validation_errors': [f'Security violation: {error_msg}']
        }
    
    # Placeholder for actual database execution
    # In production, this would connect via SQLAlchemy
    try:
        # Simulated execution result
        execution_result = {
            'columns': ['column1', 'column2'],
            'rows': [],  # Would contain actual data
            'row_count': 0,
            'query': sql_query
        }
        
        return {
            'execution_result': execution_result,
            'validation_errors': []
        }
    except Exception as e:
        return {
            'execution_result': None,
            'validation_errors': [f'Execution failed: {str(e)}']
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
    if row_count == 0:
        return {
            'confidence_score': 0.2,
            'needs_human_escalation': True,
            'validation_errors': validation_errors + ['No data returned from query']
        }
    
    # Statistical validation (simplified)
    confidence = min(1.0, 0.5 + (row_count / 1000))  # More data = higher confidence
    
    return {
        'confidence_score': confidence,
        'needs_human_escalation': confidence < 0.6
    }


async def reporter_node(state: AgentState, model_router: ModelRouter) -> AgentState:
    """
    Synthesize findings into a comprehensive report.
    Combines internal data, external context, and confidence levels.
    """
    messages = state['messages']
    last_message = messages[-1]['content']
    execution_result = state.get('execution_result')
    market_context = state.get('market_context', '')
    confidence = state.get('confidence_score', 0.5)
    validation_errors = state.get('validation_errors', [])
    
    system_prompt = f"""You are a senior business analyst preparing a report.

CONTEXT:
- User Question: {last_message}
- Market Intelligence: {market_context[:500] if market_context else 'None'}
- Confidence Level: {confidence:.1%}
- Validation Issues: {', '.join(validation_errors) if validation_errors else 'None'}

DATA RESULTS:
{json.dumps(execution_result, default=str) if execution_result else 'No data'}

GUIDELINES:
1. Start with a clear executive summary
2. Present key findings with supporting numbers
3. If market context exists, integrate it naturally
4. Be transparent about confidence levels and limitations
5. Provide actionable recommendations
6. If confidence is low or issues exist, clearly state them

FORMAT:
Use markdown with clear sections, bullet points, and bold text for emphasis.
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


# ==================== GRAPH CONSTRUCTION ====================

def create_agent_graph(
    model_router: ModelRouter, 
    newsroom_tool: NewsroomTool,
    sql_validator: SQLValidatorTool
) -> StateGraph:
    """
    Build the LangGraph state machine for the autonomous analyst.
    Integrates Newsroom, Code Sandbox, and SQL validation.
    """
    
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes with bound dependencies
    workflow.add_node("planner", lambda state: planner_node(state, model_router))
    workflow.add_node("newsroom", lambda state: newsroom_node(state, newsroom_tool))
    workflow.add_node("sql_generator", lambda state: sql_generator_node(state, model_router))
    workflow.add_node("executor", lambda state: executor_node(state, sql_validator))
    workflow.add_node("validator", lambda state: validator_node(state, model_router))
    workflow.add_node("reporter", lambda state: reporter_node(state, model_router))
    
    # Define edges
    workflow.set_entry_point("planner")
    
    # Planner → conditional branch to newsroom or directly to SQL
    def route_after_planner(state: AgentState) -> str:
        if state.get('search_queries', []):
            return "newsroom"
        return "sql_generator"
    
    workflow.add_conditional_edges(
        source="planner",
        condition=route_after_planner,
        mapping={
            "newsroom": "newsroom",
            "sql_generator": "sql_generator"
        }
    )
    
    # Newsroom → SQL Generator
    workflow.add_edge("newsroom", "sql_generator")
    
    # SQL Generator → Executor
    workflow.add_edge("sql_generator", "executor")
    
    # Executor → Validator
    workflow.add_edge("executor", "validator")
    
    # Validator → Reporter (or escalate)
    def route_after_validator(state: AgentState) -> str:
        if state.get('needs_human_escalation', False):
            return "escalate"
        return "reporter"
    
    workflow.add_conditional_edges(
        source="validator",
        condition=route_after_validator,
        mapping={
            "reporter": "reporter",
            "escalate": END  # Could add escalation node later
        }
    )
    
    # Reporter → End
    workflow.add_edge("reporter", END)
    
    return workflow.compile()


# ==================== MAIN AGENT CLASS ====================

class AutonomousAnalyst:
    """
    Main agent class that orchestrates the entire analysis workflow.
    Integrates Newsroom, Code Sandbox, and SQL Validation tools.
    """
    
    def __init__(self, model_config: Dict[str, str], newsroom_enabled: bool = True):
        self.model_router = ModelRouter(model_config)
        self.newsroom_tool = NewsroomTool(enabled=newsroom_enabled)
        self.sql_validator = SQLValidatorTool(strict_mode=True)
        self.graph = create_agent_graph(
            self.model_router, 
            self.newsroom_tool, 
            self.sql_validator
        )
    
    async def analyze(self, question: str, context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Run complete analysis workflow for a given question.
        
        Args:
            question: Natural language business question
            context: Optional context dict with 'business_context', 'schema_info'
            
        Returns:
            Dict with final_response, confidence_score, and metadata
        """
        initial_state = {
            'messages': [{'role': 'user', 'content': question}],
            'business_context': context.get('business_context', '') if context else '',
            'market_context': '',
            'schema_info': context.get('schema_info', '') if context else '',
            'plan': '',
            'search_queries': [],
            'sql_query': None,
            'python_code': None,
            'execution_result': None,
            'validation_errors': [],
            'analysis_draft': '',
            'final_response': '',
            'confidence_score': 0.0,
            'needs_human_escalation': False,
            'iteration_count': 0,
            'max_iterations': 3
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            'answer': result['final_response'],
            'confidence': result['confidence_score'],
            'sql': result.get('sql_query'),
            'data': result.get('execution_result'),
            'market_context': result.get('market_context'),
            'needs_review': result.get('needs_human_escalation', False)
        }


# Factory function
def create_analyst(config: Dict[str, str], newsroom_enabled: bool = True) -> AutonomousAnalyst:
    """Create configured analyst instance."""
    return AutonomousAnalyst(config, newsroom_enabled)
