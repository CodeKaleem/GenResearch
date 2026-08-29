# ============================================================
# Prompt: Draft Agent
# ============================================================

DRAFT_SYSTEM = """You are GenResearch Draft Agent, an expert academic writer. You produce \
publication-quality research paper drafts that are:

1. **RAG-grounded**: Every claim must be supported by the provided sources.
2. **Citation-registry bound**: You may ONLY cite sources from the provided citation registry. \
   Never invent, fabricate, or hallucinate a citation. If you cannot find a source for a claim, \
   mark it with [CITATION NEEDED] — do NOT make one up.
3. **Structured**: Follow the approved outline exactly.
4. **Academic**: Formal language, proper paragraph structure, logical flow.

Citation rules:
- Reference citations by their registry ID: [CR-001], [CR-002], etc.
- These will be resolved to full citations in post-processing.
- Every paragraph that makes a factual claim should have at least one citation.
- Prioritize user-provided sources (tagged "user") over scraped sources.

Quality targets:
- Each section should be substantive (300-800 words depending on section type).
- Transitions between sections should be smooth.
- The literature review should synthesize, not just list sources.
- Methodology should be specific and replicable.
"""

# Few-shot exemplars embedded in prompts per spec §7.4
# (prompt engineering, not fine-tuning)
FEW_SHOT_EXEMPLARS = """
=== EXEMPLAR 1: Good Academic Introduction ===
The rapid advancement of transformer-based architectures has fundamentally reshaped natural language \
processing, enabling models to achieve human-level performance across diverse linguistic tasks \
[CR-001]. However, the computational demands of these models present significant barriers to \
deployment in resource-constrained environments [CR-002]. This tension between model capability \
and practical accessibility has motivated a growing body of research into efficient inference \
techniques [CR-003, CR-004]. The present study addresses this gap by proposing a novel pruning \
strategy that maintains 95% of baseline performance while reducing computational requirements by 60%.

=== EXEMPLAR 2: Good Literature Synthesis ===
While Smith et al. [CR-005] demonstrated the effectiveness of knowledge distillation for model \
compression, their approach was limited to encoder-only architectures. In contrast, Chen and \
Wang [CR-006] extended these techniques to decoder models but reported significant degradation \
in generative tasks. More recently, Park et al. [CR-007] proposed a hybrid approach combining \
distillation with structured pruning, achieving promising results on translation benchmarks. \
However, none of these works addressed the specific challenges posed by multi-modal transformers, \
which represent the fastest-growing segment of deployed AI systems [CR-008]. This gap in the \
literature motivates our investigation.
"""


def build_draft_prompt(
    topic: str,
    outline: dict,
    citation_registry: list[dict],
    rag_context: str,
    citation_style: str = "apa",
    approval_comment: str = "",
) -> str:
    # Build outline instructions
    sections_text = ""
    for i, section in enumerate(outline.get("sections", []), 1):
        name = section.get("name", f"Section {i}")
        guidance = section.get("guidance", "")
        needs = section.get("needs", "")
        subsections = ", ".join(section.get("subsections", []))
        sections_text += f"\n### Section {i}: {name}\n"
        if subsections:
            sections_text += f"Subsections: {subsections}\n"
        if needs:
            sections_text += f"Source needs: {needs}\n"
        if guidance:
            sections_text += f"Guidance: {guidance}\n"

    # Build citation registry reference
    registry_text = ""
    for entry in citation_registry:
        cid = entry.get("id", "?")
        title = entry.get("title", "Unknown")
        authors = entry.get("authors", "Unknown")
        year = entry.get("year", "n.d.")
        tag = entry.get("tag", "scraped")
        registry_text += f"[{cid}] {authors} ({year}). {title} [{tag}]\n"

    user_feedback_section = ""
    if approval_comment:
        user_feedback_section = f"""
═══════════════════════════════════════
USER FEEDBACK & REQUESTED EDITS:
═══════════════════════════════════════
{approval_comment}
"""

    return f"""Write a complete, publication-ready research paper draft.

RESEARCH TOPIC: {topic}
CITATION STYLE: {citation_style.upper()}
{user_feedback_section}
═══════════════════════════════════════
APPROVED OUTLINE:
═══════════════════════════════════════
{sections_text}

═══════════════════════════════════════
CITATION REGISTRY (use ONLY these — never invent citations):
═══════════════════════════════════════
{registry_text}

═══════════════════════════════════════
RETRIEVED SOURCE CONTENT (RAG context):
═══════════════════════════════════════
{rag_context}

═══════════════════════════════════════
STYLE EXEMPLARS (follow this quality level):
═══════════════════════════════════════
{FEW_SHOT_EXEMPLARS}

Now compose the complete research paper draft. Follow the outline structure exactly (taking into account any USER FEEDBACK). \
Cite sources using their registry IDs (e.g., [CR-001]). Mark any unsupported claims with [CITATION NEEDED]."""
