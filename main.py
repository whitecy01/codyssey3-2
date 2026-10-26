"""AI 기반 Git 커밋 메시지 / PR 초안 생성기 CLI.

사용법:
    python main.py commit [옵션]
    python main.py pr [--base main] [옵션]
"""

import argparse
import sys

from gitgen import ai_client, formatter, git_utils, prompts, safe_mode

SEPARATOR = "-" * 40


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def section(title: str, content: str) -> None:
    print(f"\n--- {title} ---")
    print(content)
    print(SEPARATOR)


def count_lines(diff: str) -> int:
    return len(diff.splitlines())


def prepare_diff(diff: str, args) -> tuple[str, list[str]]:
    """safe-mode가 켜져 있으면 마스킹 + 전송량 제한을 적용한다."""
    notes: list[str] = []
    if not args.safe_mode:
        return diff, notes
    diff, masked = safe_mode.mask_sensitive(diff)
    info(f"safe-mode: 민감정보 {masked}건 마스킹")
    diff, notes = safe_mode.limit_diff(diff)
    for note in notes:
        info(f"safe-mode: {note}")
    return diff, notes


def call_ai(system: str, user: str, args) -> str:
    info(f"AI API 요청 중... (model={args.model}, max_tokens={args.max_tokens}"
         + (f", temperature={args.temperature}" if args.temperature is not None else "")
         + (f", effort={args.effort}" if args.effort else "") + ")")
    text = ai_client.generate(
        system=system,
        user=user,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        effort=args.effort,
    )
    info("AI API 호출 횟수: 1회")
    return text


def cmd_commit(args) -> int:
    status = git_utils.get_status()
    if not status.files:
        info("변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.")
        return 0

    staged = git_utils.get_staged_diff()
    if staged.strip():
        diff, label = staged, "git diff --cached"
        status = status.staged_only()
        info(f"Git status 수집 완료: 스테이징된 파일 {len(status.files)}개 기준으로 생성")
    else:
        diff, label = git_utils.get_unstaged_diff(), "git diff"
        info(f"Git status 수집 완료: {len(status.files)}개 파일 변경 감지 (스테이징된 파일 없음)")
    info(f"Git diff 수집 완료: {count_lines(diff)}줄 ({label})")

    diff, notes = prepare_diff(diff, args)
    user = prompts.build_user_prompt(status, diff, label, notes)
    text = call_ai(prompts.COMMIT_SYSTEM, user, args)

    message, warnings = formatter.format_commit(formatter.parse_json(text))
    print("[DONE] 커밋 메시지 생성 완료")
    for w in warnings:
        warn(w)
    section("Commit Message", message)
    return 0


def cmd_pr(args) -> int:
    status = git_utils.get_status()
    info(f"현재 브랜치: {status.branch}")

    diff, label = "", ""
    if status.branch != args.base:
        try:
            diff = git_utils.get_branch_diff(args.base)
            label = f"git diff {args.base}...HEAD"
        except git_utils.GitError:
            warn(f"'{args.base}' 브랜치와 비교할 수 없어 작업 중인 변경 사항으로 생성합니다. (--base로 기준 브랜치 지정 가능)")
    if not diff.strip():
        diff = git_utils.get_staged_diff() + git_utils.get_unstaged_diff()
        label = "git diff --cached + git diff"

    if not diff.strip() and not status.files:
        info("변경 사항이 없습니다. PR 초안을 생성하지 않고 종료합니다.")
        return 0
    info(f"Git diff 수집 완료: {count_lines(diff)}줄 ({label})")

    diff, notes = prepare_diff(diff, args)
    user = prompts.build_user_prompt(status, diff, label, notes)
    text = call_ai(prompts.PR_SYSTEM, user, args)

    title, body, warnings = formatter.format_pr(formatter.parse_json(text))
    print("[DONE] PR 초안 생성 완료")
    for w in warnings:
        warn(w)
    section("PR Title", title)
    section("PR Body", body)
    return 0


def temperature_type(value: str) -> float:
    t = float(value)
    if not 0.0 <= t <= 1.0:
        raise argparse.ArgumentTypeError("temperature는 0.0 ~ 1.0 사이여야 합니다.")
    return t


def positive_int(value: str) -> int:
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError("1 이상의 정수여야 합니다.")
    return n


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", default=ai_client.DEFAULT_MODEL,
                        help=f"사용할 모델 (기본: {ai_client.DEFAULT_MODEL})")
    common.add_argument("--max-tokens", type=positive_int, default=ai_client.DEFAULT_MAX_TOKENS,
                        help=f"응답 최대 토큰 수 (기본: {ai_client.DEFAULT_MAX_TOKENS})")
    common.add_argument("--temperature", type=temperature_type, default=None,
                        help="0.0~1.0. 지정 시에만 전송하며 이를 지원하는 모델(예: claude-haiku-4-5)이 필요합니다 (기본: 미전송)")
    common.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default=None,
                        help="모델의 사고 깊이 (기본: 모델 기본값)")
    common.add_argument("--safe-mode", action="store_true",
                        help=f"민감정보 마스킹 + diff 전송 제한(최대 {safe_mode.MAX_FILES}개 파일, {safe_mode.MAX_LINES}줄)")

    parser = argparse.ArgumentParser(description="Git 변경 사항으로 커밋 메시지 / PR 초안을 AI로 생성합니다.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("commit", parents=[common], help="커밋 메시지 생성")
    pr = sub.add_parser("pr", parents=[common], help="PR 제목/본문 초안 생성")
    pr.add_argument("--base", default="main", help="비교 기준 브랜치 (기본: main)")
    return parser


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)  # 파이프로 받아도 [INFO]/[ERROR] 순서 유지
    args = build_parser().parse_args()
    try:
        git_utils.ensure_repo_root()
        if args.command == "commit":
            return cmd_commit(args)
        return cmd_pr(args)
    except (git_utils.GitError, ai_client.AIError, formatter.FormatError) as e:
        error(str(e))
        return 1
    except KeyboardInterrupt:
        error("사용자가 중단했습니다.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
