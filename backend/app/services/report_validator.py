"""
Ground-truth validation for simulation prediction reports.

Compares generated report sections against a user-supplied ground-truth
text (e.g. a real news article) and scores each claim as
confirmed / contradicted / not_mentioned.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .report_agent import ReportManager

logger = get_logger('mirofish.report_validator')

_REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')


def _validation_path(report_id: str) -> str:
    return os.path.join(_REPORTS_DIR, report_id, 'validation.json')


def get_cached_validation(report_id: str) -> Dict[str, Any] | None:
    path = _validation_path(report_id)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _save_validation(report_id: str, result: Dict[str, Any]):
    path = _validation_path(report_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def _extract_claims(llm: LLMClient, section_content: str) -> List[str]:
    """Extract 3-5 key factual predictions/claims from a report section."""
    prompt = (
        "Extract 3 to 5 key factual predictions or claims from the following report section. "
        "Return ONLY a JSON array of short strings, each describing one claim. "
        "Example: [\"Claim A\", \"Claim B\"]\n\n"
        f"SECTION:\n{section_content[:3000]}"
    )
    try:
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512,
        )
        if isinstance(result, list):
            return [str(c) for c in result[:5]]
        # LLM might wrap in a key
        for v in result.values():
            if isinstance(v, list):
                return [str(c) for c in v[:5]]
    except Exception as e:
        logger.warning(f"Claim extraction failed: {e}")
    return []


def _verify_claim(llm: LLMClient, claim: str, ground_truth: str) -> str:
    """Return 'confirmed', 'contradicted', or 'not_mentioned'."""
    prompt = (
        f"Ground truth text:\n{ground_truth[:4000]}\n\n"
        f"Claim: {claim}\n\n"
        "Does the ground truth text CONFIRM, CONTRADICT, or NOT MENTION this claim? "
        "Reply with exactly one word: confirmed, contradicted, or not_mentioned."
    )
    try:
        answer = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=20,
        ).strip().lower()
        for keyword in ("confirmed", "contradicted", "not_mentioned"):
            if keyword in answer:
                return keyword
    except Exception as e:
        logger.warning(f"Claim verification failed: {e}")
    return "not_mentioned"


def validate_report(report_id: str, ground_truth: str) -> Dict[str, Any]:
    """
    Compare report predictions against ground_truth text.
    Results are cached in uploads/reports/<report_id>/validation.json.
    """
    # Return cached result if available
    cached = get_cached_validation(report_id)
    if cached:
        return cached

    llm = LLMClient()
    sections_raw = ReportManager.get_generated_sections(report_id)
    if not sections_raw:
        raise ValueError(f"No sections found for report {report_id}")

    section_results = []
    all_confirmed = 0
    all_contradicted = 0

    for sec in sections_raw:
        content = sec.get("content", "")
        # Derive a title from the first heading in the markdown
        title = ""
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        if not title:
            title = f"Section {sec.get('section_index', '?')}"

        claims = _extract_claims(llm, content)
        verified = []
        contradicted_list = []

        for claim in claims:
            verdict = _verify_claim(llm, claim, ground_truth)
            if verdict == "confirmed":
                verified.append(claim)
                all_confirmed += 1
            elif verdict == "contradicted":
                contradicted_list.append(claim)
                all_contradicted += 1

        total = len(verified) + len(contradicted_list)
        section_score = round(len(verified) / total * 100) if total > 0 else None

        section_results.append({
            "section_index": sec.get("section_index"),
            "section_title": title,
            "key_claims": claims,
            "verified": verified,
            "contradicted": contradicted_list,
            "score": section_score,
        })

    # Overall score: mean of sections that have a score
    scored = [s["score"] for s in section_results if s["score"] is not None]
    overall_score = round(sum(scored) / len(scored)) if scored else None

    # One-line LLM summary
    summary = ""
    try:
        summary_prompt = (
            f"In one sentence, summarize how accurately a simulation predicted the events "
            f"described in the ground truth. The simulation scored {overall_score}% overall "
            f"({all_confirmed} confirmed claims, {all_contradicted} contradicted claims)."
        )
        summary = llm.chat(
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.5,
            max_tokens=100,
        ).strip()
    except Exception:
        pass

    result = {
        "report_id": report_id,
        "overall_score": overall_score,
        "total_confirmed": all_confirmed,
        "total_contradicted": all_contradicted,
        "sections": section_results,
        "summary": summary,
        "validated_at": datetime.now().isoformat(),
    }

    _save_validation(report_id, result)
    return result
