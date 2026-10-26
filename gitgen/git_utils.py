"""git status / git diff 실행 결과를 수집한다."""

import os
import subprocess
from dataclasses import dataclass, field


class GitError(Exception):
    pass


@dataclass
class GitStatus:
    branch: str
    files: list[tuple[str, str]] = field(default_factory=list)  # (XY 상태 코드, 경로)

    @property
    def untracked(self) -> list[str]:
        return [path for code, path in self.files if code == "??"]

    def staged_only(self) -> "GitStatus":
        """스테이징된(인덱스에 올라간) 파일만 남긴 사본."""
        files = [(code, path) for code, path in self.files if code[0] not in " ?"]
        return GitStatus(branch=self.branch, files=files)


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise GitError("git 명령을 찾을 수 없습니다. Git이 설치되어 있는지 확인하세요.")
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout


def ensure_repo_root() -> None:
    """현재 디렉토리가 Git 프로젝트 루트인지 확인한다."""
    if not os.path.exists(".git"):
        raise GitError(
            "현재 디렉토리가 Git 프로젝트 루트가 아닙니다. "
            "git init이 된 프로젝트의 루트 디렉토리에서 실행하세요."
        )


def get_status() -> GitStatus:
    output = run_git(["status", "--porcelain=v1", "-b", "--untracked-files=all"])
    branch = "(unknown)"
    files = []
    for line in output.splitlines():
        if line.startswith("## "):
            branch = _parse_branch(line[3:])
        elif line.strip():
            code, path = line[:2], line[3:]
            files.append((code, path))
    return GitStatus(branch=branch, files=files)


def _parse_branch(header: str) -> str:
    # 예: "main...origin/main [ahead 1]", "No commits yet on main"
    for prefix in ("No commits yet on ", "Initial commit on "):
        if header.startswith(prefix):
            return header[len(prefix):]
    return header.split("...")[0].split(" ")[0]


def get_staged_diff() -> str:
    return run_git(["diff", "--cached"])


def get_unstaged_diff() -> str:
    return run_git(["diff"])


def get_branch_diff(base: str) -> str:
    """base 브랜치에서 갈라진 이후 현재 브랜치(HEAD)의 커밋 변경분."""
    return run_git(["diff", f"{base}...HEAD"])
