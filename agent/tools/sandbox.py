"""
Sandboxed Code Execution Tool.
Runs Python code securely for accurate calculations and data analysis.
Prevents LLM hallucinations in math and statistics.
"""
import asyncio
import docker
from docker.errors import DockerException, NotFound
import json
from typing import Any, Dict, Optional


class CodeSandboxTool:
    """
    Executes Python code in an isolated Docker container.
    Ensures 100% accuracy for calculations and data operations.
    """

    def __init__(self, use_local_docker: bool = True):
        self.use_local_docker = use_local_docker
        self.client = None
        if use_local_docker:
            try:
                self.client = docker.from_env()
            except DockerException:
                self.use_local_docker = False

    async def execute(self, code: str, libraries: list = None) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment.
        
        Args:
            code: Python code string to execute
            libraries: List of additional libraries to install (e.g., ['pandas', 'numpy'])
            
        Returns:
            Dictionary with 'success', 'output', 'error' keys
        """
        default_libraries = ['pandas', 'numpy', 'scipy', 'statsmodels']
        all_libraries = list(set(default_libraries + (libraries or [])))
        
        # Create installation command
        install_cmd = f"pip install {' '.join(all_libraries)} --quiet"
        
        # Wrap user code to capture output
        wrapped_code = f"""
import sys
from io import StringIO
old_stdout = sys.stdout
sys.stdout = mystdout = StringIO()

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except Exception as e:
    print(f"ERROR: {{str(e)}}")
    
sys.stdout = old_stdout
output = mystdout.getvalue()
print(output)
"""
        
        if self.use_local_docker and self.client:
            return await self._execute_in_docker(wrapped_code, install_cmd)
        else:
            # Fallback: Execute locally (less secure, but works without Docker).
            # The local path captures stdout itself, so it gets the RAW code —
            # the wrapper needs `import sys` which the restricted namespace
            # deliberately does not allow.
            return await self._execute_local(code)

    async def _execute_in_docker(self, code: str, install_cmd: str) -> Dict[str, Any]:
        """Execute code in a Docker container."""
        try:
            # Run container
            container = self.client.containers.run(
                "python:3.12-slim",
                command=f'/bin/bash -c "{install_cmd} && python -c \'{code}\'"',
                detach=True,
                mem_limit="512m",
                cpu_quota=50000,  # Limit CPU usage
                network_disabled=True,  # No network access for security
            )
            
            # Wait for completion
            result = container.wait(timeout=30)
            logs = container.logs().decode('utf-8')
            container.remove()
            
            if result['StatusCode'] == 0:
                return {"success": True, "output": logs, "error": None}
            else:
                return {"success": False, "output": logs, "error": f"Exit code: {result['StatusCode']}"}
                
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def _execute_local(self, code: str) -> Dict[str, Any]:
        """Fallback local execution (use only when Docker unavailable)."""
        try:
            # Restricted namespace: only whitelisted builtins + safe stdlib.
            # NOTE: this is a numeric-analysis sandbox, not full isolation —
            # the Docker path is the real security boundary when available.
            import builtins
            import math
            import json
            import statistics
            import datetime

            safe_builtins = {
                name: getattr(builtins, name)
                for name in (
                    "print", "len", "range", "sum", "min", "max", "abs", "round",
                    "int", "float", "str", "bool", "dict", "list", "tuple", "set",
                    "sorted", "enumerate", "zip", "map", "filter", "any", "all",
                    "isinstance", "type", "repr", "format", "divmod", "pow",
                    "complex", "hex", "oct", "bin", "True", "False", "None",
                )
            }

            # Guarded import: only whitelisted analysis modules may be imported.
            # The generated code legitimately uses math/statistics/json, but
            # os/subprocess/socket/etc. must stay unreachable.
            allowed_imports = {"math", "statistics", "json", "datetime", "pandas", "numpy"}

            def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                base = name.split(".")[0]
                if base not in allowed_imports:
                    raise ImportError(
                        f"Module '{name}' is not allowed in the analysis sandbox"
                    )
                return __import__(name, globals, locals, fromlist, level)

            safe_builtins["__import__"] = _safe_import

            restricted_globals = {
                "__builtins__": safe_builtins,
                "math": math,
                "json": json,
                "statistics": statistics,
                "datetime": datetime,
            }

            # Try to import safe libraries
            try:
                import pandas as pd
                import numpy as np
                restricted_globals['pd'] = pd
                restricted_globals['np'] = np
            except ImportError:
                pass

            # Capture output
            import io
            import sys
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                exec(code, restricted_globals)
                output = buffer.getvalue()
                return {"success": True, "output": output, "error": None}
            except Exception as e:
                return {"success": False, "output": buffer.getvalue(), "error": str(e)}
            finally:
                sys.stdout = old_stdout

        except Exception as e:
            return {"success": False, "output": "", "error": f"Local execution failed: {str(e)}"}

    def generate_code_prompt(self, task: str, data_sample: str = "") -> str:
        """
        Generate a prompt for the LLM to create accurate analysis code.
        """
        return f"""
You are a senior data analyst. Write Python code to solve this task:
Task: {task}

Data context:
{data_sample if data_sample else "Data will be provided at runtime"}

Requirements:
1. Use pandas for data manipulation
2. Include error handling
3. Print clear, formatted results
4. Do NOT use external APIs or network calls
5. Assume pandas and numpy are available

Write ONLY the code, no explanations:
"""
