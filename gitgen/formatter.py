"""AI 응답을 파싱하고 길이/형식 규칙을 적용(후처리)한다."""

import json

COMMIT_SUBJECT_RECOMMENDED = 50
COMMIT_SUBJECT_MAX = 72
PR_TITLE_MAX = 80
PR_SECTIONS = [("why", "Why"), ("what", "What"), ("how_to_test", "How to Test")]
PLACEHOLDER = "(작성 필요: AI가 이 섹션을 채우지 못했습니다)"


class FormatError(Exception):
    pass


def parse_json(text: str) -> dict:
    """응답에서 JSON 객체를 꺼낸다. 코드 블록 등이 섞여 있어도 첫 { ~ 마지막 } 구간을 시도한다."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise FormatError(f"AI 응답에서 JSON을 찾을 수 없습니다.\n--- 원본 응답 ---\n{text}")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise FormatError(f"AI 응답 JSON 파싱 실패: {e}\n--- 원본 응답 ---\n{text}")
    if not isinstance(data, dict):
        raise FormatError("AI 응답이 JSON 객체 형식이 아닙니다.")
    return data


def _one_line(value) -> str:
    return " ".join(str(value or "").split())


def _bullets(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    items = [_one_line(v).lstrip("-*• ").strip() for v in value]
    return [item for item in items if item]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    if " " in cut[limit // 2:]:  # 단어 중간에서 끊기지 않게
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,.") + "…"


def format_commit(data: dict) -> tuple[str, list[str]]:
    """(커밋 메시지, 경고 목록)"""
    warnings = []
    subject = _one_line(data.get("subject")).rstrip(".")
    if not subject:
        raise FormatError("AI 응답에 커밋 제목(subject)이 없습니다.")
    if len(subject) > COMMIT_SUBJECT_MAX:
        warnings.append(f"커밋 제목이 {len(subject)}자로 최대 {COMMIT_SUBJECT_MAX}자를 넘어 잘랐습니다.")
        subject = _truncate(subject, COMMIT_SUBJECT_MAX)
    elif len(subject) > COMMIT_SUBJECT_RECOMMENDED:
        warnings.append(f"커밋 제목이 {len(subject)}자입니다. ({COMMIT_SUBJECT_RECOMMENDED}자 이내 권장)")

    body = _bullets(data.get("body"))[:3]
    message = subject
    if body:
        message += "\n\n" + "\n".join(f"- {item}" for item in body)
    return message, warnings


def format_pr(data: dict) -> tuple[str, str, list[str]]:
    """(PR 제목, PR 본문, 경고 목록)"""
    warnings = []
    title = _one_line(data.get("title")).rstrip(".")
    if not title:
        raise FormatError("AI 응답에 PR 제목(title)이 없습니다.")
    if len(title) > PR_TITLE_MAX:
        warnings.append(f"PR 제목이 {len(title)}자로 최대 {PR_TITLE_MAX}자를 넘어 잘랐습니다.")
        title = _truncate(title, PR_TITLE_MAX)

    sections = []
    for key, header in PR_SECTIONS:
        items = _bullets(data.get(key))
        if not items:
            warnings.append(f"'{header}' 섹션이 비어 있어 placeholder를 넣었습니다. 직접 채워 주세요.")
            items = [PLACEHOLDER]
        sections.append(f"## {header}\n" + "\n".join(f"- {item}" for item in items))
    return title, "\n\n".join(sections), warnings
