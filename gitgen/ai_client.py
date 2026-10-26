"""Claude Messages API를 REST(urllib)로 호출한다."""

import json
import os
import socket
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
API_KEY_ENV = "AI_API_KEY"
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_MAX_TOKENS = 16000

API_VERSION = "2026-10-21"
# 2026-10-21 버전부터 temperature는 모든 모델에서 거부된다.
# --temperature를 지정하면 이전 버전으로 요청해 이를 지원하는 모델(예: claude-haiku-4-5)에서 쓸 수 있게 한다.
LEGACY_API_VERSION = "2023-06-01"

# 서버 측 refusal fallback("default" 모드)을 지원하는 모델
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"

STATUS_HINTS = {
    400: "잘못된 요청입니다. 모델 이름이나 파라미터(--temperature, --max-tokens 등)를 확인하세요.",
    401: "인증 실패: API Key가 올바르지 않습니다.",
    403: "권한이 없습니다. API Key의 권한을 확인하세요.",
    404: "요청한 리소스(모델)를 찾을 수 없습니다. --model 값을 확인하세요.",
    413: "요청이 너무 큽니다. --safe-mode로 diff 전송량을 줄여 보세요.",
    429: "요청 한도 초과(rate limit) 또는 크레딧 부족입니다. 잠시 후 다시 시도하세요.",
    500: "AI 서버 내부 오류입니다. 잠시 후 다시 시도하세요.",
    529: "AI 서버가 과부하 상태입니다. 잠시 후 다시 시도하세요.",
}


class AIError(Exception):
    pass


def get_api_key() -> str:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise AIError(
            f"{API_KEY_ENV} 환경변수가 설정되지 않았습니다.\n"
            f'## 예) export {API_KEY_ENV}="YOUR_KEY"'
        )
    return key


def generate(
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float | None = None,
    effort: str | None = None,
    timeout: float = 120,
) -> str:
    """프롬프트를 보내고 응답 텍스트를 돌려준다. 실패 시 AIError."""
    api_key = get_api_key()

    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    }
    if temperature is not None:
        body["temperature"] = temperature
        headers["anthropic-version"] = LEGACY_API_VERSION
    if effort:
        body["output_config"] = {"effort": effort}
    if model in FALLBACK_MODELS and temperature is None:
        body["fallbacks"] = "default"
        headers["anthropic-beta"] = FALLBACK_BETA

    request = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise AIError(_describe_http_error(e)) from None
    except urllib.error.URLError as e:
        raise AIError(f"네트워크 오류: AI 서버에 연결할 수 없습니다. ({e.reason})") from None
    except (TimeoutError, socket.timeout):
        raise AIError(f"요청 시간 초과: {timeout:.0f}초 안에 응답이 없습니다.") from None
    except json.JSONDecodeError:
        raise AIError("AI 서버 응답을 JSON으로 해석할 수 없습니다.") from None

    stop_reason = data.get("stop_reason")
    if stop_reason == "refusal":
        raise AIError("AI가 요청 처리를 거절했습니다(refusal). diff 내용을 확인하거나 --safe-mode를 사용하세요.")

    text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    ).strip()
    if stop_reason == "max_tokens":
        raise AIError("응답이 max_tokens 제한에 걸려 잘렸습니다. --max-tokens 값을 늘려 다시 시도하세요.")
    if not text:
        raise AIError("AI 응답에 텍스트가 없습니다.")
    return text


def _describe_http_error(e: urllib.error.HTTPError) -> str:
    detail = ""
    try:
        payload = json.loads(e.read().decode("utf-8"))
        error = payload.get("error", {})
        detail = f"{error.get('type', '')}: {error.get('message', '')}".strip(": ")
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        pass
    hint = STATUS_HINTS.get(e.code, "API 호출에 실패했습니다.")
    message = f"API 호출 실패 (HTTP {e.code}) - {hint}"
    if detail:
        message += f"\n         서버 메시지: {detail}"
    return message
