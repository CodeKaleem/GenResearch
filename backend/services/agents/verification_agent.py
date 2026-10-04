"""Claim extraction and evidence verification for generated sections."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any

from models.schemas import ExtractedClaim, GeneratedSection, VerificationResult
from services.llm_service import call_llm
from services import tracking
from services.citation_formatting import ground_ungrounded_specifics
from services.text_utils import split_sentences
from services.agents.json_utils import parse_llm_json

logger = logging.getLogger(__name__)


EVIDENCE_TAG = re.compile(r"\[(E\d+|CR-\d{3})\]")
PLACEHOLDER = re.compile(r"\b(?:CITATION\s+NEEDED|TODO|TBD)\b", re.IGNORECASE)


def _claim_id(section: str, text: str) -> str:
    return hashlib.sha256(f"{section}:{text}".encode("utf-8")).hexdigest()[:20]


def extract_claims_from_text(section_text: str, section_name: str) -> list[ExtractedClaim]:
    """Extract factual-looking sentences and their [E#] evidence tags."""
    claims: list[ExtractedClaim] = []
    for sentence in split_sentences(section_text.strip()):
        sentence = sentence.strip()
        if not sentence or len(sentence.split()) < 4:
            continue
        if sentence.endswith(":"):
            continue
        claims.append(ExtractedClaim(
            claim_id=_claim_id(section_name, sentence),
            text=sentence,
            cited_chunk_ids=EVIDENCE_TAG.findall(sentence),
            section=section_name,
        ))
    return claims


def _parse_json_object(raw: str) -> dict[str, Any]:
    value = parse_llm_json(raw)
    if value is None:
        raise ValueError("Verification model did not return a JSON object.")
    return value


async def verify_claim(
    claim: ExtractedClaim,
    excerpt_map: dict[str, str],
) -> VerificationResult:
    """Verify one claim, applying no-evidence rules before using the LLM."""
    if not claim.cited_chunk_ids:
        return VerificationResult(
            claim_id=claim.claim_id,
            verdict="unsupported",
            discrepancy="Claim has no evidence tag.",
        )
    if any(not excerpt_map.get(tag) for tag in claim.cited_chunk_ids):
        return VerificationResult(
            claim_id=claim.claim_id,
            verdict="unsupported",
            discrepancy="A cited evidence excerpt is unavailable.",
        )
    if PLACEHOLDER.search(claim.text):
        return VerificationResult(
            claim_id=claim.claim_id,
            verdict="unsupported",
            discrepancy="Claim contains an unresolved placeholder.",
        )

    excerpts = "\n\n".join(
        f"[{tag}] {excerpt_map.get(tag, '[MISSING EXCERPT]')}"
        for tag in claim.cited_chunk_ids
    )
    raw = await call_llm(
        f'''Claim: "{claim.text}"

Cited excerpts:
{excerpts}

Does the evidence support this exact claim? Return only JSON:
{{"verdict":"supported|unsupported|partial","discrepancy":"...","corrected_text":"..."}}''',
        agent_role="verification",
        system="You verify academic claims conservatively. Never infer unsupported facts.",
        temperature=0.0,
        max_tokens=300,
    )
    data = _parse_json_object(raw)
    verdict = data.get("verdict")
    if verdict not in {"supported", "unsupported", "partial"}:
        raise ValueError(f"Invalid verification verdict: {verdict!r}")
    return VerificationResult(
        claim_id=claim.claim_id,
        verdict=verdict,
        discrepancy=data.get("discrepancy") or None,
        corrected_text=data.get("corrected_text") or None,
    )


async def verify_section(
    section: GeneratedSection,
    excerpt_map: dict[str, str],
    session_id: str = "",
    topic: str = "",
) -> GeneratedSection:
    """Ground and verify claims; generic uncited prose is marked, unsupported specifics are removed."""
    grounding = ground_ungrounded_specifics(
        section.text,
        excerpt_map,
        set(excerpt_map),
        topic,
    )
    claims = extract_claims_from_text(grounding.text, section.section_name)
    semaphore = asyncio.Semaphore(3)

    async def safely_verify(claim: ExtractedClaim) -> VerificationResult:
        async with semaphore:
            try:
                return await verify_claim(claim, excerpt_map)
            except Exception as error:
                logger.warning(
                    "claim_verification_failed",
                    extra={"section": section.section_name, "claim_id": claim.claim_id},
                    exc_info=True,
                )
                return VerificationResult(
                    claim_id=claim.claim_id,
                    verdict="unsupported",
                    discrepancy=f"verifier error: {type(error).__name__}: {error}",
                )

    results = await asyncio.gather(*(safely_verify(claim) for claim in claims))
    for claim, result in zip(claims, results):
        tracking.save_generated_claim(
            session_id=session_id,
            section=section.section_name,
            claim_text=claim.text,
            cited_chunk_ids=claim.cited_chunk_ids,
            verdict=result.verdict,
            discrepancy=result.discrepancy,
            corrected_text=result.corrected_text,
        )
    text = grounding.text
    removed_claims = list(grounding.removed_claims)
    verifier_removed: list[str] = []
    for claim, result in zip(claims, results):
        if result.verdict == "unsupported" and not PLACEHOLDER.search(claim.text):
            text = text.replace(claim.text, "").strip()
            verifier_removed.append(claim.text)
        elif result.verdict == "partial" and result.corrected_text:
            text = text.replace(claim.text, result.corrected_text)
    if not text.strip() and (grounding.text.strip() or verifier_removed):
        text = grounding.text
        verifier_removed = []
    removed_claims.extend(verifier_removed)
    flagged_count = grounding.flagged_count + len(verifier_removed)
    under_evidenced = grounding.preserved_empty_section or (
        grounding.sentence_count > 0
        and flagged_count / grounding.sentence_count > 0.5
    )
    return section.model_copy(update={
        "text": text,
        "claims": claims,
        "verification": results,
        "removed_claims": removed_claims,
        "under_evidenced": under_evidenced,
        "verified": True,
    })