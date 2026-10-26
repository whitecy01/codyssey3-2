"""커밋 / PR 생성용 프롬프트."""

from .git_utils import GitStatus

COMMIT_SYSTEM = """당신은 Git 변경 사항을 읽고 커밋 메시지를 작성하는 시니어 개발자입니다.
주어진 git status와 git diff만 근거로 작성하고, diff에 없는 내용은 지어내지 마세요.

작성 규칙:
- subject: Conventional Commits 형식 "<type>: <요약>" 한 줄.
  type은 feat, fix, refactor, docs, style, test, chore, perf, build, ci 중 하나.
  요약은 한국어로, 무엇을 왜 바꿨는지 드러나게 쓰고 마침표로 끝내지 마세요.
  전체 50자 이내를 목표로 하고 72자를 절대 넘기지 마세요.
- body: 핵심 변경 사항 1~3개. 각 항목은 한 문장이며 변경된 파일 또는 모듈 이름을 1개 이상 포함하세요.
  변경이 아주 사소하면 빈 배열이어도 됩니다.
- 여러 성격의 변경이 섞여 있으면 가장 중요한 변경을 subject에 쓰고 나머지는 body에 쓰세요.

출력은 아래 JSON 객체 하나만 내보내세요. 코드 블록이나 다른 설명은 붙이지 마세요.
{"subject": "feat: ...", "body": ["...", "..."]}"""

PR_SYSTEM = """당신은 Git 변경 사항을 읽고 Pull Request 제목과 본문을 작성하는 시니어 개발자입니다.
주어진 git status와 git diff만 근거로 작성하고, diff에 없는 내용은 지어내지 마세요.
변경 배경(why)이 diff로 확실히 드러나지 않으면 diff에서 합리적으로 추론할 수 있는 수준까지만 쓰세요.

작성 규칙:
- title: "<type>: <요약>" 한 줄, 한국어, 80자 이내. type은 feat, fix, refactor, docs, test, chore 등.
- why: 변경 배경과 목적. 1~3개 항목.
- what: 핵심 변경 사항. 2~5개 항목. 가능하면 파일/모듈 이름을 포함하세요.
- how_to_test: 리뷰어가 따라 할 수 있는 구체적인 확인 절차. 1~4개 항목. 실행 명령이 있으면 포함하세요.
- 각 항목은 한 문장이며, 앞에 "-" 같은 불릿 기호를 붙이지 마세요.

출력은 아래 JSON 객체 하나만 내보내세요. 코드 블록이나 다른 설명은 붙이지 마세요.
{"title": "...", "why": ["..."], "what": ["..."], "how_to_test": ["..."]}"""


def build_user_prompt(status: GitStatus, diff: str, diff_label: str, notes: list[str]) -> str:
    file_lines = "\n".join(f"{code} {path}" for code, path in status.files) or "(없음)"
    parts = [
        f"현재 브랜치: {status.branch}",
        f"<git_status>\n{file_lines}\n</git_status>",
        f"<git_diff source=\"{diff_label}\">\n{diff.strip() or '(diff 없음)'}\n</git_diff>",
    ]
    if status.untracked:
        parts.append(
            "참고: 상태 코드 ??는 새로 추가되어 아직 추적되지 않는 파일이며 diff에 내용이 포함되지 않습니다. "
            "파일 이름으로만 판단하세요."
        )
    if notes:
        parts.append("참고: " + " / ".join(notes) + ". 전송되지 않은 부분은 추측하지 마세요.")
    return "\n\n".join(parts)
