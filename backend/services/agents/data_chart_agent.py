"""Generate charts from extracted tables without allowing invented data."""
from __future__ import annotations

import json

from services.code_exec_service import run_sandboxed
from services.llm_service import call_llm


async def generate_chart(table_data: dict, request: str, output_dir: str | None = None) -> dict:
    code = await call_llm(
        f"""Write Python using only pandas, matplotlib, numpy, and json to answer: {request!r}.
The input table is available in data.json. Do not invent values. Save the chart as output.png
and print computed values as JSON.
TABLE DATA: {json.dumps(table_data)}""",
        agent_role="composer",
        temperature=0.0,
        max_tokens=500,
    )
    return run_sandboxed(code, table_data, output_dir=output_dir)