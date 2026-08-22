"""
Sandboxed Code Execution Tool.
Runs Python code securely for accurate calculations and data analysis.
Prevents LLM hallucinations in math and statistics.

Security model (strongest available boundary wins):

1. AST allowlist — the code is parsed before it runs and rejected if it
   contains imports outside the numeric allowlist, attribute access to
   dunder internals, or calls to eval/exec/open/__import__. This runs on
   BOTH paths, so malformed or hostile code never reaches an interpreter.
2. Docker — when a Docker daemon is reachable, code runs in a throwaway
   container with no network, a memory cap, and a wall-clock timeout.
   This is the real isolation boundary.
3. In-process fallback — restricted globals with a guarded __import__ and
   a wall-clock timeout. Defence in depth only: the AST gate is what makes
   this path acceptable, not the namespace restriction, which a determined
   attacker can escape. Operators who need a hard guarantee should keep
   Docker available or disable the sandbox entirely.
"""
import ast
import asyncio
from typing import Any, Dict, List, Optional, Set

try:
    import docker
except ImportError:  # docker SDK is optional at runtime
    docker = None

# Modules the generated analysis code may import.
ALLOWED_IMPORTS: Set[str] = {
    "math", "statistics", "json", "datetime", "decimal", "fractions",
    "itertools", "functools", "collections", "re",
}

# Names that would break out of the restricted namespace.
FORBIDDEN_NAMES: Set[str] = {
    "eval", "exec", "compile", "open", "input", "__import__", "globals",
    "locals", "vars", "getattr", "setattr", "delattr", "breakpoint",
    "memoryview", "exit", "quit", "help",
}

DEFAULT_TIMEOUT_SECONDS = 20
DOCKER_IMAGE = "python:3.12-slim"
MAX_CODE_BYTES = 100_000


class SandboxSecurityError(Exception):
    """Raised when generated code violates the sandbox policy."""


def validate_code(code: str) -> None:
    """
    Static gate: parse the code and reject anything outside the policy.

    Raises SandboxSecurityError with a specific reason so the failure is
    visible in the audit log rather than silently degrading.
    """
    if not code or not code.strip():
        raise SandboxSecurityError("Empty code")
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        raise SandboxSecurityError("Code exceeds maximum size")

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxSecurityError(f"Syntax error: {e}") from e

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    raise SandboxSecurityError(f"Import of '{alias.name}' is not allowed")

        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise SandboxSecurityError(f"Import from '{node.module}' is not allowed")

        elif isinstance(node, ast.Attribute):
            # Blocks the classic __class__/__subclasses__/__globals__ escape.
            if node.attr.startswith("__") and node.attr.endswith("__"):
                raise SandboxSecurityError(
                    f"Access to dunder attribute '{node.attr}' is not allowed"
                )

        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                raise SandboxSecurityError(f"Use of '{node.id}' is not allowed")


class CodeSandboxTool:
    """
    Executes Python code in an isolated environment.
    Ensures accuracy for calculations by running real code instead of
    trusting model arithmetic.
    """

    def __init__(
        self,
        use_local_docker: bool = True,
        enabled: bool = True,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        allow_local_fallback: bool = True,
    ):
        self.enabled = enabled
        self.timeout = timeout
        self.allow_local_fallback = allow_local_fallback
        self.client = None

        if use_local_docker and enabled and docker is not None:
            try:
                client = docker.from_env()
                client.ping()
                self.client = client
            except Exception:
                # No daemon reachable (common inside the app's own container).
                self.client = None

    @property
    def use_local_docker(self) -> bool:
        """Whether the Docker boundary is actually available."""
        return self.client is not None

    @property
    def isolation(self) -> str:
        """Which boundary is in effect — surfaced to the UI and audit log."""
        if not self.enabled:
            return "disabled"
        if self.client:
            return "docker"
        return "in-process" if self.allow_local_fallback else "unavailable"

    async def execute(self, code: str, libraries: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment.

        Args:
            code: Python code string to execute
            libraries: ignored; the sandbox runs stdlib-only by policy

        Returns:
            Dictionary with 'success', 'output', 'error', 'isolation' keys.
        """
        if not self.enabled:
            return {
                "success": False,
                "output": "",
                "error": "Code sandbox is disabled in configuration.",
                "isolation": "disabled",
            }

        try:
            validate_code(code)
        except SandboxSecurityError as e:
            return {
                "success": False,
                "output": "",
                "error": f"Sandbox policy violation: {e}",
                "isolation": self.isolation,
            }

        if self.client:
            return await self._execute_in_docker(code)
        if not self.allow_local_fallback:
            return {
                "success": False,
                "output": "",
                "error": "Docker unavailable and in-process fallback is disabled.",
                "isolation": "unavailable",
            }
        return await self._execute_local(code)

    async def _execute_in_docker(self, code: str) -> Dict[str, Any]:
        """Execute code in a throwaway container with no network."""

        def run() -> Dict[str, Any]:
            container = None
            try:
                # List form avoids shell interpolation of the generated code.
                container = self.client.containers.run(
                    DOCKER_IMAGE,
                    command=["python", "-c", code],
                    detach=True,
                    mem_limit="512m",
                    pids_limit=64,
                    cpu_quota=50000,
                    network_disabled=True,
                    read_only=True,
                    user="nobody",
                )
                result = container.wait(timeout=self.timeout)
                logs = container.logs().decode("utf-8", errors="replace")
                status = result.get("StatusCode", 1)
                return {
                    "success": status == 0,
                    "output": logs,
                    "error": None if status == 0 else f"Exit code: {status}",
                    "isolation": "docker",
                }
            except Exception as e:
                return {"success": False, "output": "", "error": str(e), "isolation": "docker"}
            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

        return await asyncio.to_thread(run)

    async def _execute_local(self, code: str) -> Dict[str, Any]:
        """
        Fallback in-process execution, used only when Docker is unavailable.

        The AST gate has already rejected imports, dunder access, and escape
        builtins; this adds a restricted namespace and a wall-clock timeout.
        """
        import builtins
        import contextlib
        import io

        safe_builtin_names = (
            "abs", "all", "any", "bin", "bool", "chr", "complex", "dict",
            "divmod", "enumerate", "filter", "float", "format", "frozenset",
            "hex", "int", "isinstance", "issubclass", "iter", "len", "list",
            "map", "max", "min", "next", "oct", "ord", "pow", "print", "range",
            "repr", "reversed", "round", "set", "slice", "sorted", "str",
            "sum", "tuple", "type", "zip",
        )
        safe_builtins: Dict[str, Any] = {
            name: getattr(builtins, name)
            for name in safe_builtin_names
            if hasattr(builtins, name)
        }
        safe_builtins.update({"True": True, "False": False, "None": None})

        def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.split(".")[0] not in ALLOWED_IMPORTS:
                raise ImportError(f"Module '{name}' is not allowed in the analysis sandbox")
            return __import__(name, globals, locals, fromlist, level)

        safe_builtins["__import__"] = _safe_import

        import datetime as _datetime
        import json as _json
        import math as _math
        import statistics as _statistics

        restricted_globals: Dict[str, Any] = {
            "__builtins__": safe_builtins,
            "math": _math,
            "json": _json,
            "statistics": _statistics,
            "datetime": _datetime,
        }

        def run() -> Dict[str, Any]:
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    exec(code, restricted_globals)
                return {
                    "success": True,
                    "output": buffer.getvalue(),
                    "error": None,
                    "isolation": "in-process",
                }
            except Exception as e:
                return {
                    "success": False,
                    "output": buffer.getvalue(),
                    "error": str(e),
                    "isolation": "in-process",
                }

        try:
            return await asyncio.wait_for(asyncio.to_thread(run), timeout=self.timeout)
        except asyncio.TimeoutError:
            # The worker thread cannot be force-killed; it is left to finish
            # while the caller gets a clean timeout. The AST gate rejects
            # network and file access, so a runaway is CPU-only.
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {self.timeout}s",
                "isolation": "in-process",
            }

    def generate_code_prompt(self, task: str, data_sample: str = "") -> str:
        """Generate a prompt for the LLM to create accurate analysis code."""
        return f"""
You are a senior data analyst. Write Python code to solve this task:
Task: {task}

Data context:
{data_sample if data_sample else "Data will be provided at runtime"}

Requirements:
1. Use only these standard library modules: {', '.join(sorted(ALLOWED_IMPORTS))}
2. Include error handling
3. Print clear, formatted results
4. Do NOT use external APIs, network calls, or file access

Write ONLY the code, no explanations:
"""
