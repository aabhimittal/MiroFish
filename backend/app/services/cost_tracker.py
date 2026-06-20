"""
LLM API cost tracking.
Appends one JSON record per call to uploads/costs/<context_id>.jsonl
and supports per-context budget enforcement.
"""

import os
import json
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..config import Config

_COSTS_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/costs')
_lock = threading.Lock()


class BudgetExceededError(Exception):
    pass


def _cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens / 1000 * Config.LLM_COST_PER_1K_INPUT_TOKENS
        + completion_tokens / 1000 * Config.LLM_COST_PER_1K_OUTPUT_TOKENS
    )


def record_call(
    context_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Append a cost record and return the call cost in USD."""
    cost = _cost_usd(prompt_tokens, completion_tokens)
    record: Dict[str, Any] = {
        "ts": datetime.now().isoformat(),
        "context_id": context_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost,
    }
    os.makedirs(_COSTS_DIR, exist_ok=True)
    fpath = os.path.join(_COSTS_DIR, f"{context_id}.jsonl")
    with _lock:
        with open(fpath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + "\n")
    return cost


def get_total_cost(context_id: str) -> float:
    """Return total USD spent for a context."""
    return sum(r["cost_usd"] for r in get_cost_breakdown(context_id))


def get_cost_breakdown(context_id: str) -> List[Dict[str, Any]]:
    """Return all cost records for a context."""
    fpath = os.path.join(_COSTS_DIR, f"{context_id}.jsonl")
    if not os.path.exists(fpath):
        return []
    records = []
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def check_budget(context_id: str, budget_usd: Optional[float] = None) -> None:
    """Raise BudgetExceededError if the context has exceeded its budget."""
    if budget_usd is None:
        budget_usd = Config.DEFAULT_BUDGET_USD_PER_SIMULATION
    if budget_usd <= 0:
        return
    spent = get_total_cost(context_id)
    if spent >= budget_usd:
        raise BudgetExceededError(
            f"Budget exceeded for {context_id}: spent ${spent:.4f} of ${budget_usd:.2f}"
        )


def get_summary() -> List[Dict[str, Any]]:
    """Return per-context cost summary for all tracked contexts."""
    os.makedirs(_COSTS_DIR, exist_ok=True)
    summaries = []
    for fname in os.listdir(_COSTS_DIR):
        if not fname.endswith('.jsonl'):
            continue
        context_id = fname[:-6]
        records = get_cost_breakdown(context_id)
        if not records:
            continue
        summaries.append({
            "context_id": context_id,
            "total_cost_usd": sum(r["cost_usd"] for r in records),
            "total_calls": len(records),
            "total_prompt_tokens": sum(r["prompt_tokens"] for r in records),
            "total_completion_tokens": sum(r["completion_tokens"] for r in records),
            "first_call": records[0]["ts"],
            "last_call": records[-1]["ts"],
        })
    return sorted(summaries, key=lambda x: x["total_cost_usd"], reverse=True)
