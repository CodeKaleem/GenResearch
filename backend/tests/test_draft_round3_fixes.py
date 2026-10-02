"""
Regression tests for four issues found in a real draft after the previous
round of fixes:

1. The model copied exemplar placeholder bracket syntax literally —
   "[Author A, Year] [CR-00X]" — into real output. Fixed with a
   deterministic backstop (flag_placeholder_template_syntax) plus
   bracket-free exemplars.
2. Duplicate section headings persisted in a third distinct form
   ("**Section 1: Introduction**") despite an explicit prompt instruction.
   Fixed with a deterministic backstop (_strip_duplicate_leading_heading)
   instead of a fourth prompt-wording attempt.
3. The model invented specific real-world entities (a named drug falsely
   attributed to the wrong disease) even while marking the sentence
   [CITATION NEEDED] — the flag doesn't make a fabricated specific fact
   acceptable. Fixed with an explicit prompt prohibition.
4. context_build_node assigned the same top-3 registry entries to every
   section regardless of topical relevance. Fixed with keyword-overlap
   relevance scoring (_select_relevant_sources).
"""
import asyncio

from services.agents.nodes.context_build import context_build_node, _select_relevant_sources
from services.agents.nodes.draft import _strip_duplicate_leading_heading
from services.agents.prompts.draft import DRAFT_SYSTEM
from services.citation_formatting import flag_placeholder_template_syntax, resolve_and_append_references


# ---- Fix 1: placeholder bracket syntax ----

def test_flags_copied_author_year_bracket_placeholder():
    text = "A study by [Author A, Year] ([CR-00X]) showed promising results."
    result = flag_placeholder_template_syntax(text)
    assert "Author A" not in result
    assert "CR-00X" not in result
    assert result.count("[CITATION NEEDED]") == 2


def test_real_cr_tag_survives_placeholder_flagging():
    text = "A real citation [CR-001] stays untouched."
    result = flag_placeholder_template_syntax(text)
    assert "[CR-001]" in result


def test_resolve_and_append_references_also_catches_placeholder_syntax():
    draft = "Evidence here ([Author B, Year] [CR-00Y])."
    out = resolve_and_append_references(draft, citation_registry=[])
    assert "Author B" not in out
    assert "CR-00Y" not in out


# ---- Fix 2: duplicate headings ----

def test_strips_bold_section_number_heading():
    generated = "**Section 1: Introduction**\n\nReal body text starts here."
    result = _strip_duplicate_leading_heading(generated, "Introduction")
    assert result == "Real body text starts here."


def test_strips_bare_repeated_heading():
    generated = "Introduction\n\nReal body text."
    result = _strip_duplicate_leading_heading(generated, "Introduction")
    assert result == "Real body text."


def test_strips_markdown_section_number_heading():
    generated = "### Section 1: Introduction\nReal body text."
    result = _strip_duplicate_leading_heading(generated, "Introduction")
    assert result == "Real body text."


def test_leaves_genuine_content_untouched():
    generated = "AI has transformed medical science in several ways."
    result = _strip_duplicate_leading_heading(generated, "Introduction")
    assert result == generated


# ---- Fix 3: fabricated specific entities ----

def test_prompt_forbids_fabricated_specific_entities():
    assert "specific" in DRAFT_SYSTEM.lower()
    assert "case stud" in DRAFT_SYSTEM.lower()
    assert "does not license inventing" in DRAFT_SYSTEM or "not license inventing" in DRAFT_SYSTEM


# ---- Fix 4: relevance-based source assignment ----

def test_sections_get_topically_relevant_sources_not_the_same_slice():
    registry = [
        {"id": "CR-001", "title": "Deep learning for radiology imaging diagnostics"},
        {"id": "CR-002", "title": "Survey research methodology and data collection design"},
    ]
    imaging_sources = _select_relevant_sources("Diagnostics", "radiology imaging", registry)
    methods_sources = _select_relevant_sources("Methodology", "research methodology design", registry)

    assert [s["id"] for s in imaging_sources] == ["CR-001"]
    assert [s["id"] for s in methods_sources] == ["CR-002"]


def test_no_relevant_source_returns_honest_empty_list_not_arbitrary_slice():
    registry = [{"id": "CR-001", "title": "Completely unrelated astrophysics topic"}]
    result = _select_relevant_sources("Methodology", "data collection", registry)
    assert result == []


def test_context_build_assigns_different_sources_per_section():
    state = {
        "outline": {
            "sections": [
                {"name": "Diagnostics", "guidance": "radiology imaging deep learning"},
                {"name": "Methodology", "guidance": "survey research methodology design"},
            ]
        },
        "citation_registry": [
            {"id": "CR-001", "title": "Deep learning for radiology imaging diagnostics"},
            {"id": "CR-002", "title": "Survey research methodology and data collection design"},
        ],
    }
    result = asyncio.run(context_build_node(state))
    diag_ids = {s["id"] for s in result["section_contexts"][0]["assigned_sources"]}
    method_ids = {s["id"] for s in result["section_contexts"][1]["assigned_sources"]}
    assert diag_ids != method_ids
