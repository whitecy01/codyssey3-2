"""--safe-mode: 민감정보 마스킹(A) + diff 전송량 제한(B)."""

import re

MAX_FILES = 10
MAX_LINES = 200

MASK_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("API_KEY", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}")),               # Anthropic / OpenAI
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GOOGLE_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("RRN", re.compile(r"\b\d{6}-[1-4]\d{6}\b")),                       # 주민등록번호
    ("PHONE", re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")),
]

# password = "..." / API_KEY: ... 처럼 키 이름 뒤에 오는 값
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:api[_-]?key|secret|password|passwd|token)[A-Za-z0-9_]*)"
    r"(\s*[:=]\s*)(['\"]?)([^\s'\"]{4,})(['\"]?)"
)


def mask_sensitive(text: str) -> tuple[str, int]:
    """민감정보를 [MASKED_<종류>]로 치환하고 (결과, 치환 횟수)를 돌려준다."""
    count = 0
    for name, pattern in MASK_PATTERNS:
        text, n = pattern.subn(f"[MASKED_{name}]", text)
        count += n

    def _mask_value(m: re.Match) -> str:
        nonlocal count
        value = m.group(4)
        # 이미 마스킹된 값, os.environ.get(...) 같은 코드 표현식은 그대로 둔다
        if value.startswith("[MASKED_") or "(" in value:
            return m.group(0)
        count += 1
        return f"{m.group(1)}{m.group(2)}{m.group(3)}[MASKED_SECRET]{m.group(5)}"

    text = SECRET_ASSIGNMENT.sub(_mask_value, text)
    return text, count


def limit_diff(diff: str, max_files: int = MAX_FILES, max_lines: int = MAX_LINES) -> tuple[str, list[str]]:
    """diff를 최대 파일 수 / 최대 줄 수로 자른다. (결과, 안내 메시지 목록)"""
    notes = []
    chunks = re.split(r"(?m)^(?=diff --git )", diff)
    chunks = [c for c in chunks if c.strip()]
    if len(chunks) > max_files:
        notes.append(f"파일 {len(chunks)}개 중 {max_files}개만 전송")
        chunks = chunks[:max_files]

    lines = "".join(chunks).splitlines()
    if len(lines) > max_lines:
        notes.append(f"diff {len(lines)}줄 중 {max_lines}줄만 전송")
        lines = lines[:max_lines] + ["... (safe-mode: 이후 내용 생략)"]
    return "\n".join(lines), notes
