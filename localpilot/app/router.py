"""The brain: analyze -> decide -> call local/cloud -> escalate if needed -> metrics."""
import logging
import time
from typing import Any, Dict, List, Optional

from . import config
from .analyzer import analyze
from .context import optimize_context, redact_text, repo_stats
from .llm import LLMResult, call_cloud, call_local
from .tokens import count_tokens

log = logging.getLogger("localpilot.router")


def decide(score: float) -> str:
    if score < config.LOCAL_THRESHOLD:
        return "local"
    if score > config.CLOUD_THRESHOLD:
        return "cloud"
    return "local_first"


def preview(prompt: str, repo_path: Optional[str] = None, code: str = "") -> Dict[str, Any]:
    """Dry run: the routing decision and token estimates, without calling any model.
    Lets a UI ask the user for consent before anything is sent to the cloud."""
    repo_tokens, num_files = repo_stats(repo_path)
    analysis = analyze(prompt, code=code, repo_context_tokens=repo_tokens, num_repo_files=num_files)
    ctx = optimize_context(prompt, repo_path, code=code, token_budget=config.CLOUD_CONTEXT_TOKEN_BUDGET)
    prompt_tokens = count_tokens(prompt)
    return {
        "decision": decide(analysis.score),
        "complexity_score": analysis.score,
        "task_type": analysis.task_type,
        "factors": analysis.factors,
        "reasons": analysis.reasons,
        "original_tokens": prompt_tokens + ctx.original_tokens,
        "estimated_cloud_tokens": prompt_tokens + ctx.optimized_tokens,
        "files_selected": ctx.files_selected,
        "secrets_redacted": ctx.secrets_redacted,
        "context_optimizer": ctx.optimizer,
        "min_local_confidence": config.MIN_LOCAL_CONFIDENCE,
        "cloud_provider": config.CLOUD_PROVIDER,
    }


async def handle(prompt: str, repo_path: Optional[str] = None, code: str = "", force_route: str = "auto") -> Dict[str, Any]:
    start = time.perf_counter()
    trace: List[str] = []

    repo_tokens, num_files = repo_stats(repo_path)
    analysis = analyze(prompt, code=code, repo_context_tokens=repo_tokens, num_repo_files=num_files)
    decision = decide(analysis.score) if force_route == "auto" else force_route
    trace.append(f"score={analysis.score} -> {decision}")

    # Cloud-only baseline: what a normal assistant would send (prompt + all code/repo)
    ctx = optimize_context(prompt, repo_path, code=code, token_budget=config.CLOUD_CONTEXT_TOKEN_BUDGET)
    baseline_tokens = count_tokens(prompt) + ctx.original_tokens

    local: Optional[LLMResult] = None
    cloud: Optional[LLMResult] = None
    escalated = False
    escalation_reason = None

    if decision in ("local", "local_first"):
        try:
            # Local model is private, so it can see the same optimized context
            local = await call_local(prompt, ctx.context)
            trace.append(f"local confidence={local.confidence} needs_cloud={local.needs_cloud}")
            if local.confidence < config.MIN_LOCAL_CONFIDENCE:
                escalation_reason = f"local confidence {local.confidence} < {config.MIN_LOCAL_CONFIDENCE}"
            elif local.needs_cloud:
                escalation_reason = "local model flagged needs_cloud"
        except Exception as e:
            log.exception("local model failed")
            escalation_reason = f"local model error: {e}"
        if escalation_reason and force_route != "local":
            escalated = True
            trace.append(f"escalating: {escalation_reason}")

    prompt_secrets = 0
    if decision == "cloud" or escalated:
        # Only the cloud path needs redaction: local never leaves the machine
        cloud_prompt, prompt_secrets = redact_text(prompt)
        cloud = await call_cloud(cloud_prompt, ctx.context)

    final = cloud or local
    if final is None:
        raise RuntimeError(escalation_reason or "no model produced an answer")

    sent_tokens = cloud.input_tokens if cloud else 0
    return {
        "answer": final.answer,
        "route": "cloud" if cloud else "local",
        "model": final.model,
        "escalated": escalated,
        "escalation_reason": escalation_reason if escalated else None,
        "confidence": local.confidence if local else None,
        "complexity_score": analysis.score,
        "task_type": analysis.task_type,
        "factors": analysis.factors,
        "reasons": analysis.reasons,
        "original_tokens": baseline_tokens,
        "sent_tokens": sent_tokens,
        "tokens_saved": max(baseline_tokens - sent_tokens, 0),
        "files_selected": ctx.files_selected,
        "secrets_redacted": (ctx.secrets_redacted + prompt_secrets) if cloud else 0,
        "redaction_details": ctx.redaction_details if cloud else [],
        "context_optimizer": ctx.optimizer,
        "latency_ms": int((time.perf_counter() - start) * 1000),
        "local_latency_ms": local.latency_ms if local else None,
        "cloud_latency_ms": cloud.latency_ms if cloud else None,
        "trace": trace,
    }
