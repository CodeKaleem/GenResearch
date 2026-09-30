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
- Reference citations only by their exact registry ID: [CR-001], [CR-002], etc.
- Never write freeform author/year citations such as "(Smith et al., 2020)". If no registry ID
    supports a claim, mark it [CITATION NEEDED].
- These will be resolved to full citations in post-processing.
- Every paragraph that makes a factual claim should have at least one citation.
- Prioritize user-provided sources (tagged "user") over scraped sources.
- If the citation registry and retrieved source content below are thin or only tangentially \
    related to the topic, that is a REAL constraint, not a gap to paper over: write shorter, \
    narrower sections and mark unsupported claims with [CITATION NEEDED] rather than inventing \
    plausible-sounding detail to fill the space.

Output-structure rules (violating these corrupts the assembled document — follow exactly):
- Do NOT repeat the section title as the first line of your output, in plain text OR bold \
    markdown. The heading is inserted automatically by the assembly step; starting your response \
    with the section name (or a bolded restatement of it) produces a duplicated heading.
- Do NOT write your own "References," "Bibliography," or "Works Cited" list anywhere in your \
    output, in any section, including the last one. The complete reference list is generated \
    automatically from the citation registry after every section is assembled. Any reference list \
    you write yourself will be fabricated by definition, since you do not have real bibliographic \
    detail beyond what's in the registry above — do not attempt it.
- Do NOT insert [FIGURE:...] or similar figure/image placeholder tags. Figure generation is not \
    currently supported by this pipeline; if a section would benefit from a figure, describe the \
    data in prose instead of tagging a placeholder for one.

Quality targets:
- Each section should be substantive (300-800 words depending on section type) WHEN the \
    available sources support that length — do not pad a thinly-sourced section to hit a word \
    target.
- Transitions between sections should be smooth.
- The literature review should synthesize, not just list sources.
- Methodology should be specific and replicable.
"""

# Few-shot exemplars embedded in prompts per spec §7.4 (prompt engineering, not fine-tuning).
# These are schematic templates with placeholders only; concrete fake examples can be copied
# into drafts as unsupported content when the real retrieval context is thin.
FEW_SHOT_EXEMPLARS = """
=== EXEMPLAR 1: Introduction structure (a template, not real content) ===
[Broad framing of the field] has [transformed / reshaped / advanced] [domain], enabling \
[capability] [CR-00X]. However, [a real limitation or tension in the actual sources] presents \
[challenge] [CR-00Y]. This tension has motivated [type of research direction found in the \
actual sources] [CR-00Z]. This paper addresses [specific gap, grounded in the real material \
above] by [approach].

=== EXEMPLAR 2: Literature-synthesis structure (a template, not real content) ===
While [Author A, Year] [CR-00X] demonstrated [a real finding from the actual sources], their \
approach was limited to [a real constraint]. In contrast, [Author B, Year] [CR-00Y] extended \
this to [a broader case, if the real sources support one] but reported [a real limitation]. \
[If a third real source exists: More recently, Author C, Year [CR-00Z] proposed [approach], \
achieving [outcome].] However, [a real remaining gap in the actual sources] motivates \
[this paper's specific focus].

Remember: every bracketed placeholder above must be filled from the REAL citation registry \
and RAG context provided below — never from a remembered example, a plausible-sounding study, \
or a fabricated author name. If the real sources don't support filling a placeholder, omit that \
sentence or mark the claim [CITATION NEEDED] instead.
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
STYLE EXEMPLARS — bracketed TEMPLATES showing structure only, not real content to copy:
═══════════════════════════════════════
{FEW_SHOT_EXEMPLARS}

Now compose the complete research paper draft. Follow the outline structure exactly (taking into account any USER FEEDBACK). \
Cite sources using their registry IDs (e.g., [CR-001]). Mark any unsupported claims with [CITATION NEEDED].

Final reminders before you write:
- Do not start any section with its own title repeated as text.
- Do not write a References/Bibliography list yourself, anywhere.
- Do not insert [FIGURE:...] placeholders.
- The style exemplars above are templates with bracket placeholders — copying their wording, \
authors, or subject matter (rather than filling placeholders from the real registry and RAG \
context) produces a fabricated paper. If the real sources above are thin, write less; do not \
borrow content from the exemplars to compensate."""
