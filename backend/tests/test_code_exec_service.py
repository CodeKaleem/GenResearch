import pytest

from services.code_exec_service import UnsafeCodeError, run_sandboxed


def test_sandbox_collects_output():
    result = run_sandboxed("import json\nprint(json.dumps({'value': 3}))", {})
    assert '"value": 3' in result["stdout"]


def test_sandbox_rejects_network_imports():
    with pytest.raises(UnsafeCodeError):
        run_sandboxed("import requests", {})