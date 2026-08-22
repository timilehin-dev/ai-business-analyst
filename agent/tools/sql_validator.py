"""
SQL Validator Tool.
Ensures only safe, read-only SQL queries are executed.

This is the first of two layers. The second — and the authoritative one —
is the database connection itself, which is forced read-only at the engine
level (PRAGMA query_only / SET TRANSACTION READ ONLY). This validator exists
to reject bad queries early with a useful message the agent can self-correct
from, not to be the sole barrier against a hostile query.

Parsing rules that matter:
  - comments are stripped first, so an annotated query is judged on its
    statement rather than its preamble
  - string literals are blanked before keyword scanning, so a value like
    'DROP the mic' in a WHERE clause is not mistaken for DDL
"""
import re
from typing import List, Optional, Tuple

import sqlvalidator

# Statements that modify data or schema, or escalate privileges.
DANGEROUS_KEYWORDS = frozenset({
    "DELETE", "DROP", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE", "REPLACE", "UPSERT",
    "ATTACH", "DETACH", "VACUUM", "PRAGMA", "SET", "COPY", "CALL",
    "COMMIT", "ROLLBACK", "SAVEPOINT", "LOCK", "REINDEX", "ANALYZE",
})

# Words above that are also standard scalar functions. They are only
# dangerous as statement keywords, so a following '(' clears them —
# REPLACE(name,'a','b') is ordinary SELECT-list code, REPLACE INTO is not.
FUNCTION_SAFE_KEYWORDS = frozenset({"REPLACE", "MERGE", "ANALYZE", "LOCK", "CALL"})

# Read-only statements a query may legitimately start with.
ALLOWED_STARTS = ("SELECT", "WITH")

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def strip_sql_comments(sql: str) -> str:
    """
    Remove SQL comments (/* ... */ and -- line comments) before analysis.

    The LLM is instructed to annotate queries with comments, so validation
    must not reject a query just because it starts with a comment block.
    """
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def blank_string_literals(sql: str) -> str:
    """
    Replace the contents of quoted literals with spaces.

    Keeps the quotes and overall length so positions stay meaningful, while
    ensuring keyword scanning never reads user data as SQL syntax.
    """
    out = []
    i = 0
    length = len(sql)
    while i < length:
        char = sql[i]
        if char in ("'", '"', "`"):
            quote = char
            out.append(quote)
            i += 1
            while i < length:
                # Doubled quote is an escaped quote inside the literal.
                if sql[i] == quote and i + 1 < length and sql[i + 1] == quote:
                    out.append("  ")
                    i += 2
                    continue
                if sql[i] == quote:
                    out.append(quote)
                    i += 1
                    break
                out.append(" ")
                i += 1
        else:
            out.append(char)
            i += 1
    return "".join(out)


def split_statements(sql: str) -> List[str]:
    """Split on semicolons that are not inside string literals."""
    masked = blank_string_literals(sql)
    statements = []
    start = 0
    for index, char in enumerate(masked):
        if char == ";":
            chunk = sql[start:index].strip()
            if chunk:
                statements.append(chunk)
            start = index + 1
    tail = sql[start:].strip()
    if tail:
        statements.append(tail)
    return statements


class SQLValidatorTool:
    """
    Validates SQL queries for safety and correctness.
    Blocks any non-SELECT statements.
    """

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

        clean = strip_sql_comments(sql)
        if not clean.strip():
            return False, "Query contains only comments"

        statements = split_statements(clean)
        if not statements:
            return False, "No executable statement found"
        if len(statements) > 1:
            return False, (
                f"Multiple statements detected ({len(statements)}). "
                "Only a single SELECT is allowed."
            )

        statement = statements[0]
        masked = blank_string_literals(statement)
        upper = masked.upper().strip()

        if not upper.startswith(ALLOWED_STARTS):
            return False, f"Only SELECT queries are allowed. Blocked: {sql.strip()[:80]}"

        dangerous = self._dangerous_keywords(upper)
        if dangerous:
            return False, f"Dangerous operation detected: {', '.join(sorted(dangerous))}"

        # `SELECT ... INTO new_table` writes despite starting with SELECT.
        if re.search(r"\bINTO\b", upper) and not re.search(r"\bINSERT\b", upper):
            return False, "SELECT ... INTO is not allowed (it writes a new table)"

        try:
            parsed = sqlvalidator.parse(statement)
            if not parsed.is_valid():
                return False, f"SQL syntax error: {parsed.errors}"
        except Exception as e:
            # sqlvalidator only understands a subset of dialects; a parse
            # crash on valid vendor SQL must not block the query, since the
            # database itself is the authoritative syntax check.
            if self.strict_mode:
                return False, f"SQL validation failed: {str(e)}"

        return True, None

    @staticmethod
    def _dangerous_keywords(upper_sql: str) -> List[str]:
        """
        Dangerous keywords used as statements rather than as functions.

        Scans the literal-masked, uppercased SQL so values never trigger a
        match, and clears keywords immediately followed by '(' since those
        are scalar function calls.
        """
        found = []
        for match in _WORD_RE.finditer(upper_sql):
            word = match.group()
            if word not in DANGEROUS_KEYWORDS:
                continue
            if word in FUNCTION_SAFE_KEYWORDS:
                rest = upper_sql[match.end():].lstrip()
                if rest.startswith("("):
                    continue
            found.append(word)
        return sorted(set(found))

    def suggest_fix(self, sql: str, error: str) -> str:
        """Generate a prompt for the LLM to fix the SQL query."""
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
