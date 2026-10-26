# AI Git 커밋/PR 자동 생성기

`git status`와 `git diff` 결과를 AI(Claude API)에 보내 **커밋 메시지**와 **PR 제목/본문 초안**을 만들어 주는 Python CLI입니다.
생성된 문구는 초안이므로 터미널에서 확인한 뒤 복사해서 사용하세요. 이 도구는 커밋, push, PR 생성을 직접 하지 않습니다.

## 동작 흐름

```
git status / git diff 수집 → (--safe-mode: 마스킹·전송 제한) → 프롬프트 구성
→ Claude Messages API 1회 호출(REST) → JSON 응답 파싱 → 길이/형식 검증·후처리 → 터미널 출력
```

## 프로젝트 구조

```
main.py               CLI 진입점 (commit / pr 명령, 옵션 처리, 출력)
gitgen/
  git_utils.py        git status / git diff 실행과 파싱
  prompts.py          커밋/PR 시스템 프롬프트와 사용자 입력 구성
  ai_client.py        Claude API REST 호출, 오류 처리
  formatter.py        응답 JSON 파싱, 길이·템플릿 규칙 적용
  safe_mode.py        민감정보 마스킹, diff 전송량 제한
```

## 설치

- Python 3.10 이상, Git
- 외부 패키지를 쓰지 않습니다(표준 라이브러리 `urllib`로 REST 호출). 따로 설치할 것이 없습니다.

```bash
git clone <이 리포지토리 URL>
cd <리포지토리 폴더>
```

## 환경변수(API Key) 설정

[Anthropic Console](https://console.anthropic.com)에서 API Key를 발급받아 `AI_API_KEY` 환경변수로 설정합니다. 코드나 파일에 키를 적지 마세요.

```bash
# macOS / Linux (현재 터미널에서만 유효)
export AI_API_KEY="sk-ant-..."

# 계속 쓰려면 셸 설정 파일에 추가
echo 'export AI_API_KEY="sk-ant-..."' >> ~/.zshrc

# Windows PowerShell
$env:AI_API_KEY="sk-ant-..."
```

## 사용법

**커밋 메시지를 만들 프로젝트의 루트 디렉토리**에서 실행합니다. 다른 프로젝트에 쓸 때는 `main.py` 경로를 지정하면 됩니다.

```bash
cd ~/my-project
python /path/to/main.py commit
```

### 커밋 메시지 생성

```bash
python main.py commit
```

- 스테이징된 변경(`git add` 한 것)이 있으면 그것만 기준으로 생성합니다. 실제로 커밋될 내용과 맞추기 위해서입니다.
- 스테이징된 변경이 없으면 작업 디렉토리의 변경(`git diff`)을 기준으로 생성합니다.

### PR 제목/본문 생성

```bash
python main.py pr                 # main 브랜치 대비 현재 브랜치의 커밋 변경분
python main.py pr --base develop  # 기준 브랜치 지정
```

기준 브랜치와 차이가 없거나 비교할 수 없으면(예: 첫 커밋 전) 작업 중인 변경 사항으로 생성합니다.

### 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--model` | `claude-opus-5-5` | 사용할 모델 |
| `--max-tokens` | `16000` | 응답 최대 토큰 수(상한일 뿐이며 실제 사용량은 보통 훨씬 적음) |
| `--temperature` | 미전송 | 0.0~1.0. 아래 주의사항 참고 |
| `--effort` | 모델 기본값 | `low`~`max`. 모델이 얼마나 깊이 생각할지 |
| `--safe-mode` | 꺼짐 | 민감정보 마스킹 + diff 전송 제한 |
| `--base` (pr 전용) | `main` | 비교 기준 브랜치 |

```bash
python main.py commit --effort low --max-tokens 4000
python main.py pr --safe-mode
python main.py commit --model claude-haiku-4-5 --temperature 0.2
```

#### 파라미터가 결과에 주는 영향

- **temperature**: 낮을수록(0.0) 같은 입력에 비슷한 문구가 나오고, 높을수록(1.0) 표현이 다양해집니다. 커밋 메시지처럼 형식이 정해진 글은 낮은 값이 어울립니다.
- **max_tokens**: 응답 길이의 상한입니다. 너무 작으면 응답이 중간에 잘리며, 이때 도구는 잘린 결과를 쓰지 않고 오류로 알립니다.
- **effort**: 최신 Claude 모델에서 사고 깊이와 토큰 사용량을 조절합니다. 커밋 메시지는 `low`로도 충분한 경우가 많습니다.

> **temperature 주의:** 현재 Claude API(버전 `2026-10-21`)는 모든 모델에서 `temperature`를 받지 않고, 최신 모델은 이전 버전에서도 기본값만 허용합니다.
> 그래서 이 도구는 `--temperature`를 지정했을 때만 이전 API 버전(`2023-06-01`)으로 요청합니다. 이 경우 `claude-haiku-4-5`, `claude-sonnet-4-6`처럼 temperature를 지원하는 모델을 `--model`로 함께 지정하세요. 지원하지 않는 모델이면 API가 400 오류를 반환합니다.

## 출력 예시

### 커밋 메시지

```
$ python main.py commit
[INFO] Git status 수집 완료: 스테이징된 파일 3개 기준으로 생성
[INFO] Git diff 수집 완료: 128줄 (git diff --cached)
[INFO] AI API 요청 중... (model=claude-opus-5-5, max_tokens=16000)
[INFO] AI API 호출 횟수: 1회
[DONE] 커밋 메시지 생성 완료

--- Commit Message ---
feat: Git 변경 사항 기반 커밋 메시지 자동 생성 추가

- git_utils.py에서 git status/diff 결과를 수집해 AI 입력으로 전달
- formatter.py에 커밋 제목 72자 제한과 불릿 정리 규칙 적용
- ai_client.py에 API Key 미설정·인증 실패 오류 안내 추가
----------------------------------------
```

### PR 초안

```
$ python main.py pr
[INFO] 현재 브랜치: feature/commit-pr-generator
[INFO] Git diff 수집 완료: 412줄 (git diff main...HEAD)
[INFO] AI API 요청 중... (model=claude-opus-5-5, max_tokens=16000)
[INFO] AI API 호출 횟수: 1회
[DONE] PR 초안 생성 완료

--- PR Title ---
feat: AI 기반 커밋 메시지/PR 초안 생성 CLI 추가
----------------------------------------

--- PR Body ---
## Why
- 커밋 메시지와 PR 설명 작성에 드는 시간을 줄이고 형식을 일관되게 맞추기 위해 자동 생성 도구가 필요했습니다.

## What
- git_utils.py: git status/diff 수집 로직 추가
- main.py: commit, pr 명령과 모델·파라미터 옵션 추가
- formatter.py: PR 본문을 Why/What/How to Test 템플릿으로 정리
- safe_mode.py: API Key·이메일 마스킹과 diff 전송 제한 추가

## How to Test
- export AI_API_KEY="YOUR_KEY" 로 환경변수를 설정합니다.
- 파일을 수정하고 git add 한 뒤 python main.py commit 을 실행합니다.
- python main.py pr 을 실행해 본문에 세 섹션과 불릿이 있는지 확인합니다.
----------------------------------------
```

### 오류 / 예외 상황

```
$ python main.py commit
[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.

$ python main.py commit
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
## 예) export AI_API_KEY="YOUR_KEY"

$ python main.py commit
[ERROR] API 호출 실패 (HTTP 401) - 인증 실패: API Key가 올바르지 않습니다.
         서버 메시지: authentication_error: invalid x-api-key
```

네트워크 오류, 시간 초과, 요청 한도 초과(429), 서버 과부하(529), 응답 잘림(max_tokens)도 원인과 함께 출력합니다.

## 출력 형식 검증 규칙

AI 호출 횟수를 늘리지 않기 위해 재생성하지 않고 **후처리** 방식으로 규칙을 적용합니다.
AI에게는 JSON으로 항목만 받고, 템플릿은 코드가 직접 조립하므로 섹션 헤더가 빠지는 일이 없습니다.

| 대상 | 규칙 | 처리 |
|---|---|---|
| 커밋 제목 | 50자 권장, 최대 72자 | 50자 초과 시 경고, 72자 초과 시 잘라내고 경고. 끝의 마침표 제거 |
| 커밋 본문 | 불릿 최대 3개, 파일/모듈 이름 포함 | 프롬프트로 지시, 3개 초과분 제거 |
| PR 제목 | 최대 80자, 1줄 | 초과 시 잘라내고 경고 |
| PR 본문 | `## Why` / `## What` / `## How to Test` + 섹션마다 불릿 1개 이상 | 빈 섹션은 "(작성 필요)" 불릿을 넣고 경고 |

## 민감정보와 safe-mode

`git diff` 내용은 그대로 외부 AI 서버로 전송됩니다. 설정 파일, 테스트 데이터 등에 API Key나 개인정보가 들어 있을 수 있으니, 의심되면 `--safe-mode`를 켜세요.

```bash
python main.py commit --safe-mode
```

- **(A) 마스킹**: 아래 패턴을 `[MASKED_종류]`로 바꾼 뒤 전송합니다.
  - API Key(`sk-...`), AWS Key(`AKIA...`), GitHub 토큰(`ghp_...`), Google Key(`AIza...`), Slack 토큰, JWT, Private Key 블록
  - `password`, `secret`, `token`, `api_key`가 들어간 이름에 대입된 값
  - 이메일, 휴대폰 번호, 주민등록번호
- **(B) 전송 제한**: diff를 최대 **10개 파일, 200줄**까지만 전송합니다. 잘린 사실은 프롬프트에도 알려 AI가 추측하지 않게 합니다.

마스킹은 정규표현식 기반이라 모든 민감정보를 잡아내지는 못합니다. `.env` 같은 파일은 처음부터 `.gitignore`에 넣어 diff에 포함되지 않게 하는 것이 가장 안전합니다.

## 비용과 사용 권장 사항

- 명령 1회 실행당 AI API를 **딱 1번** 호출하고, 로그에 호출 횟수를 출력합니다.
- 비용은 입력(diff 크기)과 출력 토큰 수에 비례합니다. 대규모 변경(lock 파일, 빌드 결과물 등)이 섞이면 입력이 커지므로 필요한 파일만 `git add` 한 뒤 실행하거나 `--safe-mode`로 전송량을 줄이세요.
- 더 저렴하게 쓰려면 `--effort low`나 `--model claude-haiku-5-5`처럼 가벼운 설정을 쓸 수 있습니다.
- 생성된 문구는 정답이 아닌 초안입니다. 내용이 실제 변경과 맞는지 반드시 확인한 뒤 사용하세요.
