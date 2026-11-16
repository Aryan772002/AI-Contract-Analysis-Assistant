"""Evidence-backed identification of potentially risky contract clauses."""

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .ingest import TextChunk
from .summarize import DEFAULT_MODEL


_RISK_PATTERNS = {
    "Termination": re.compile(r"\bterminat\w*|\bcancel\w*|\bnotice\b|\brenew\w*|\bexpir\w*", re.I),
    "Penalty and fees": re.compile(
        r"\bpenalt\w*|\blate fee|\binterest\b|\bliquidated damages\b|\bfine\b|\bforfeit\w*|\bnon-refundable\b|\bdamages\b",
        re.I,
    ),
    "Liability and indemnity": re.compile(
        r"\bliabilit\w*|\bindemnif\w*|\bhold harmless\b|\blimitation of liability\b", re.I
    ),
    "Payment": re.compile(r"\bpayment\b|\binvoice\b|\bfee\b|\brefund\b|\bdeposit\b", re.I),
    "Disputes and discretion": re.compile(
        r"\barbitrat\w*|\bgoverning law\b|\bsole discretion\b|\bunilater\w*|\bwaiv\w*", re.I
    ),
}
_LEVELS = {"Low", "Medium", "High"}
_CATEGORIES = set(_RISK_PATTERNS)


def _focused_candidate_sources(chunks: list[TextChunk], limit: int = 15) -> list[dict]:
    """Create category-specific, word-boundary excerpts for clearer evidence."""
    candidates = []
    for chunk in chunks:
        for category, pattern in _RISK_PATTERNS.items():
            matches = list(pattern.finditer(chunk.text))
            if not matches:
                continue
            windows = []
            for match in matches[:4]:
                start = max(0, match.start() - 110)
                end = min(len(chunk.text), match.end() + 170)
                if start > 0:
                    next_space = chunk.text.find(" ", start, end)
                    if next_space >= 0:
                        start = next_space + 1
                if end < len(chunk.text):
                    previous_space = chunk.text.rfind(" ", start, end)
                    if previous_space > start:
                        end = previous_space
                windows.append((start, end))
            windows.sort()
            merged = []
            for start, end in windows:
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            excerpt = " ... ".join(chunk.text[start:end] for start, end in merged)[:650]
            candidates.append(
                {
                    "page_number": chunk.page_number,
                    "excerpt": excerpt,
                    "matched_categories": [category],
                    "match_count": len(matches),
                }
            )
    candidates.sort(key=lambda item: (-item["match_count"], item["page_number"]))

    # Overlapping text chunks can surface the same clause more than once.
    # Compare token overlap within the same category and page, keeping the
    # clearest (highest match count) excerpt for each repeated clause.
    selected = []
    selected_tokens: list[set[str]] = []
    for candidate in candidates:
        category = candidate["matched_categories"][0]
        terms = set(re.findall(r"[a-z0-9]+", candidate["excerpt"].lower()))
        duplicate = False
        for existing, existing_terms in zip(selected, selected_tokens):
            if existing["page_number"] != candidate["page_number"]:
                continue
            if existing["matched_categories"][0] != category:
                continue
            overlap = len(terms & existing_terms) / max(1, min(len(terms), len(existing_terms)))
            if overlap >= 0.72:
                duplicate = True
                break
        if duplicate:
            continue
        selected.append(candidate)
        selected_tokens.append(terms)
        if len(selected) >= limit:
            break

    for source_id, candidate in enumerate(selected, start=1):
        candidate["source_id"] = source_id
    return selected


def analyze_contract_risks(chunks: list[TextChunk]) -> dict:
    """Find clause candidates locally, then classify them with Groq."""
    candidates = _focused_candidate_sources(chunks)
    if not candidates:
        return {
            "findings": [],
            "message": "No clauses matched the current risk scan terms.",
            "model": None,
        }

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise RuntimeError("Add your Groq API key to the backend .env file first.")
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    prompt = f"""Review these excerpts from a contract for clauses a reader may want to review.
Return one valid JSON object with a findings array. Each finding must include:
- source_id: one integer from the supplied excerpts
- title: short descriptive title
- category: one of {sorted(_CATEGORIES)}
- risk_level: exactly Low, Medium, or High
- reason: brief explanation grounded in the excerpt
- potential_impact: concise description of a possible practical impact

Use Low for routine and clear terms, Medium for terms that may create meaningful cost or obligation, and High only for unusually severe, one-sided, unclear, or potentially uncapped obligations. These labels are preliminary review signals, not legal conclusions. Do not invent clauses, quotes, page numbers, or facts. Do not provide legal advice. Return an empty findings array if nothing merits attention.

EXCERPTS:
{json.dumps(candidates, ensure_ascii=False)}
"""
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You identify contract-review signals cautiously and return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ClausewiseContractAssistant/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        data = json.loads(content)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("error", {}).get("message", body)
        except (json.JSONDecodeError, AttributeError):
            detail = body
        raise RuntimeError(f"Groq API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError("Could not connect to Groq. Check your internet connection and try again.") from exc
    except Exception as exc:
        raise RuntimeError(f"Groq risk analysis failed: {exc}") from exc

    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list):
        raise RuntimeError("The model response did not contain a valid findings list.")
    source_by_id = {item["source_id"]: item for item in candidates}
    findings = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        try:
            source_id = int(item.get("source_id"))
        except (TypeError, ValueError):
            continue
        source = source_by_id.get(source_id)
        level = item.get("risk_level")
        category = item.get("category")
        if (
            source is None
            or not isinstance(level, str)
            or level not in _LEVELS
            or not isinstance(category, str)
            or category not in _CATEGORIES
        ):
            continue
        findings.append(
            {
                "source_id": source_id,
                "page_number": source["page_number"],
                "excerpt": source["excerpt"],
                "title": str(item.get("title", "Clause for review"))[:120],
                "category": category,
                "risk_level": level,
                "reason": str(item.get("reason", ""))[:700],
                "potential_impact": str(item.get("potential_impact", ""))[:500],
            }
        )
    findings.sort(key=lambda item: ({"High": 0, "Medium": 1, "Low": 2}[item["risk_level"]], item["page_number"]))
    return {
        "findings": findings,
        "message": "Potential review signals only; verify each excerpt in the original contract.",
        "model": model,
        "candidate_count": len(candidates),
    }
