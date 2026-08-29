# ============================================================
# Node: Merge C+D (Join before Final QA)
# ============================================================
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def merge_cd_node(state: dict) -> dict:
    cv = state.get("citation_verification_result", {})
    sc = state.get("section_critic_result", {})

    return {
        "current_step": "merge_cd",
        "steps_log": [
            f"✓ Post-draft checks merged: citation={cv.get('coverage_score', '?')}, "
            f"quality={sc.get('overall_score', '?')}/10"
        ],
    }
