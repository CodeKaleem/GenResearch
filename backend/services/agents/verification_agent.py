"""Claim extraction and evidence verification for generated sections."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from models.schemas import ExtractedClaim, GeneratedSection, VerificationResult
from services.llm_service import call_llm
from services import tracking


EVIDENCE_TAG = re.compile(r"\[E(\d+)\]")
PLACEHOLDER = re.compile(r"\b(?:CITATION\s+NEEDED|TODO|TBD)\b", re.IGNORECASE)


def _claim_id(section: str, text: str) -> str:
    return hashlib.sha256(f"{section}:{text}".encode("utf-8")).hexdigest()[:20]


def extract_claims_from_text(section_text: str, section_name: str) -> list[ExtractedClaim]:
    """Extract factual-looking sentences and their [E#] evidence tags."""
    claims: list[ExtractedClaim] = []
    for sentence in re.split(r"(?<=[.!?])\s+", section_text.strip()):
        sentence = sentence.strip()
        if not sentence or len(sentence.split()) < 4:
            continue
        if sentence.endswith(":"):
            continue
        claims.append(ExtractedClaim(
            claim_id=_claim_id(section_name, sentence),
            text=sentence,
            cited_chunk_ids=[f"E{number}" for number in EVIDENCE_TAG.findall(sentence)],
            section=section_name,
        ))
    return claims


def _parse_json_object(raw: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("Verification model did not return a JSON object.")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Verification response must be a JSON object.")
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
) -> GeneratedSection:
    """Verify all claims and remove/correct unsupported generated sentences."""
    claims = extract_claims_from_text(section.text, section.section_name)
    results = [await verify_claim(claim, excerpt_map) for claim in claims]
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
    text = section.text
    for claim, result in zip(claims, results):
        if result.verdict == "unsupported":
            text = text.replace(claim.text, "").strip()
        elif result.verdict == "partial" and result.corrected_text:
            text = text.replace(claim.text, result.corrected_text)
    return section.model_copy(update={
        "text": text,
        "claims": claims,
        "verification": results,
        "verified": True,
    })