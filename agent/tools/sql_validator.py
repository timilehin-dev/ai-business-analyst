"""
SQL Validator Tool.
Ensures only safe, read-only SQL queries are executed.
Prevents accidental data modification and SQL injection.
"""
import sqlvalidator
from typing import Optional, Tuple


class SQLValidatorTool:
    """
    Validates SQL queries for safety and correctness.
    Blocks any non-SELECT statements.
    """

    ALLOWED_KEYWORDS = {"SELECT", "FROM", "WHERE", "AND", "OR", "ORDER", "BY", 
                        "LIMIT", "OFFSET", "GROUP", "HAVING", "JOIN", "LEFT", 
                        "RIGHT", "INNER", "OUTER", "ON", "AS", "DISTINCT", 
                        "COUNT", "SUM", "AVG", "MIN", "MAX", "CASE", "WHEN", 
                        "THEN", "ELSE", "END", "NULL", "IS", "NOT", "IN", 
                        "BETWEEN", "LIKE", "EXISTS", "WITH", "RECURSIVE"}

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a SQL query.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"

        # Check for dangerous keywords
        sql_upper = sql.upper().strip()
        
        # Block any statement that isn't a SELECT
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return False, "Only SELECT queries are allowed. Blocked: " + sql[:50]
        
        # Block dangerous operations even within SELECT
        dangerous_ops = ["DELETE", "DROP", "TRUNCATE", "UPDATE", "INSERT", 
                         "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"]
        
        for op in dangerous_ops:
            if op in sql_upper.split():
                return False, f"Dangerous operation detected: {op}"

        # Try to parse with sqlvalidator
        try:
            parsed = sqlvalidator.parse(sql)
            if not parsed.is_valid():
                return False, f"SQL syntax error: {parsed.errors}"
        except Exception as e:
            if self.strict_mode:
                return False, f"SQL validation failed: {str(e)}"
            # In non-strict mode, allow but warn
            pass

        # Additional heuristic checks
        if "--" in sql or ";" in sql.rstrip().rstrip(";").split("--")[0]:
            # Allow comments but check for multiple statements
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            if len(statements) > 1:
                # Check if all are SELECTs
                for stmt in statements:
                    if not stmt.upper().startswith(("SELECT", "WITH")):
                        return False, "Multiple statements detected. Only one SELECT allowed."

        return True, None

    def suggest_fix(self, sql: str, error: str) -> str:
        """
        Generate a prompt for the LLM to fix the SQL query.
        """
        return f"""
The following SQL query has an issue:

Query: {sql}
Issue: {error}

Please fix the query ensuring:
1. It remains a SELECT-only query
2. No dangerous operations (DELETE, DROP, UPDATE, etc.)
3. Valid SQL syntax
4. Proper table and column references

Provide ONLY the corrected SQL:
"""
