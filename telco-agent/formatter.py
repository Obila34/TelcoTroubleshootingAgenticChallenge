import re

FAULT_TYPES = frozenset(
    {
        "L3VPNconfigurationerror",
        "shutdown",
        "routingloopdetected",
        "interfacedown",
        "bgpsessiondown",
        "mplslabelissue",
        "vlanmisconfiguration",
    }
)


def classify_question(question: str) -> str:
    """Detect answer type from question text."""
    q = question.lower()
    # Prefer fault-style tasks before path hints: "routing" contains "route" as substring.
    if any(
        k in q
        for k in [
            "fault",
            "root cause",
            "diagnose",
            "misconfiguration",
            "error",
            "issue",
            "problem",
            "wrong",
        ]
    ):
        return "fault_tuple"
    if any(
        k in q
        for k in [
            "path",
            "traffic flow",
            "traceroute",
            "hop",
            "ip route",
            "link chain",
        ]
    ):
        return "path_trace"
    if any(k in q for k in ["interface", "port", "list", "which interface"]):
        return "interface_list"
    return "unknown"


def _normalize_semicolon_line(line: str) -> str:
    line = line.strip()
    if not line or ";" not in line:
        return line
    parts = [p.strip() for p in line.split(";")]
    if len(parts) < 2:
        return line
    if len(parts) == 2:
        return f"{parts[0]};{parts[1]}"
    rest = ";".join(parts[2:]).strip()
    return f"{parts[0]};{parts[1]};{rest}"


def _strip_markdown_noise(text: str) -> str:
    text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"^\s*#+\s*.+$", "", text, flags=re.MULTILINE)
    return text.strip()


def _pick_fault_style_line(lines: list[str]) -> str | None:
    """Prefer the last concise semicolon-separated answer line (exact-match grading)."""
    skip_prefixes = (
        "based on my",
        "routing table",
        "interface status",
        "root cause",
        "fault diagnosis",
        "configuration:",
        "the device has",
        "analysis:",
        "**routing",
        "**interface",
        "**root",
    )

    def usable(ln: str) -> bool:
        low = ln.lower().lstrip("* ")
        if any(low.startswith(p) for p in skip_prefixes):
            return False
        if low.startswith(("-", "*", "•")):
            return False
        return True

    # Prefer a true tuple (two semicolons → three fields); graders often require this shape.
    for ln in reversed(lines):
        if not usable(ln) or ";" not in ln:
            continue
        if ln.count(";") >= 2 and len(ln) <= 600:
            return ln
    for ln in reversed(lines):
        if usable(ln) and ";" in ln and len(ln) <= 600:
            return ln
    return None


def _clean_fault_or_unknown(raw: str) -> str:
    raw = _strip_markdown_noise(raw)
    for prefix in ["Answer:", "The answer is:", "Result:", "Output:", "Final answer:"]:
        if raw.lower().startswith(prefix.lower()):
            raw = raw[len(prefix) :].strip()

    cleaned_lines: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        ln = re.sub(r"^\s*[\-\*•]\s+", "", ln)
        ln = re.sub(r"^\d+\.\s+", "", ln)
        if ln:
            cleaned_lines.append(ln)

    picked = _pick_fault_style_line(cleaned_lines)
    if picked:
        return _normalize_semicolon_line(picked)

    # Fallback: any semicolon line from bottom of original text
    for ln in reversed([x.strip() for x in raw.splitlines() if x.strip()]):
        if ";" in ln and len(ln) < 500:
            return _normalize_semicolon_line(ln)

    # Single-line collapse (no semicolons): trim whitespace
    one = " ".join(raw.split())
    return one[:4000].strip()


def clean_answer(raw: str, answer_type: str) -> str:
    """Strip any explanatory text. Return only the answer — one line when possible."""
    if answer_type in ("fault_tuple", "unknown"):
        return _clean_fault_or_unknown(raw)

    raw = _strip_markdown_noise(raw)
    raw = raw.strip()

    for prefix in ["Answer:", "The answer is:", "Result:", "Output:", "Final answer:"]:
        if raw.lower().startswith(prefix.lower()):
            raw = raw[len(prefix) :].strip()

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if answer_type == "path_trace":
        for line in lines:
            if "->" in line:
                return line
        return lines[0] if lines else raw.strip()
    if lines:
        raw = "\n".join(lines)

    return raw.strip()


def validate_path_answer(answer: str) -> bool:
    parts = answer.split("->")
    return len(parts) >= 2 and all("_" in p for p in parts)


def validate_fault_tuple(answer: str) -> bool:
    lines = [ln for ln in answer.strip().split("\n") if ln.strip()]
    if not lines:
        return False
    for line in lines:
        parts = line.split(";")
        if len(parts) != 3:
            return False
        if not all(p.strip() for p in parts):
            return False
        # Legacy Zindi-style tokens; Phase-2-style tasks use human-readable reasons from the prompt.
        if parts[2].strip() in FAULT_TYPES:
            continue
        if len(parts[2].strip()) < 2:
            return False
    return True


def validate_interface_list(answer: str) -> bool:
    if not answer.strip():
        return False
    for line in answer.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if "->" in line:
            if not validate_path_answer(line):
                return False
        elif "_" not in line:
            return False
    return True


def validate_answer(answer: str, answer_type: str) -> bool:
    if not answer.strip():
        return False
    if answer_type == "path_trace":
        return validate_path_answer(answer)
    if answer_type == "fault_tuple":
        return validate_fault_tuple(answer)
    if answer_type == "interface_list":
        return validate_interface_list(answer)
    return (
        validate_path_answer(answer)
        or validate_fault_tuple(answer)
        or validate_interface_list(answer)
    )
