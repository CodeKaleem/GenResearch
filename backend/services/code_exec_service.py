"""Constrained local execution for deterministic table/chart generation."""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ALLOWED_IMPORTS = {"json", "math", "matplotlib", "numpy", "pandas"}
BLOCKED_NAMES = {"eval", "exec", "compile", "__import__", "open", "input"}


class UnsafeCodeError(ValueError):
    """Raised when generated chart code leaves the permitted subset."""


def validate_generated_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name.split(".")[0] for alias in node.names]
            if any(name not in ALLOWED_IMPORTS for name in names):
                raise UnsafeCodeError("Generated code imports a module outside the allowlist.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BLOCKED_NAMES:
            raise UnsafeCodeError(f"Generated code calls blocked builtin {node.func.id!r}.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise UnsafeCodeError("Generated code cannot access dunder attributes.")


def run_sandboxed(code: str, data: dict, timeout: int = 10, output_dir: str | Path | None = None) -> dict:
    """Run validated code in a temporary working directory.

    For production, invoke this service inside a Docker container with
    ``--network=none`` and a read-only filesystem. The subprocess mode is for
    local development and still constrains imports, cwd, and runtime.
    """
    validate_generated_code(code)
    destination = Path(output_dir) if output_dir else None
    with tempfile.TemporaryDirectory() as temporary:
        workdir = Path(temporary)
        (workdir / "data.json").write_text(json.dumps(data), encoding="utf-8")
        (workdir / "script.py").write_text(code, encoding="utf-8")
        try:
            result = subprocess.run(
                ["python3", "script.py"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"execution timed out after {timeout}s", "output_files": []}

        output_files: list[str] = []
        if destination:
            destination.mkdir(parents=True, exist_ok=True)
            for path in workdir.glob("output.*"):
                target = destination / path.name
                shutil.copyfile(path, target)
                output_files.append(str(target))
        return {"stdout": result.stdout, "stderr": result.stderr, "output_files": output_files}