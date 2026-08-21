# -*- coding: utf-8 -*-
"""
OpenAI API 호출 공통 래퍼.

MOCK 모드: OPENAI_API_KEY(환경변수) 또는 st.secrets에 키가 없으면
           실제 호출 대신 미리 정의된 모의 응답을 반환한다.
           API 키 없는 로컬 개발/UI 테스트 단계에서 비용 없이 흐름을 검증하기 위함.
"""
import json
import os
import time

try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

DEFAULT_MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.5


class JSONExtractionError(RuntimeError):
    """Raised when a model response cannot be parsed as one complete JSON object."""


def get_secret(name: str, default=None):
    value = os.environ.get(name)
    if value:
        return value
    if _HAS_ST:
        try:
            return st.secrets[name]
        except Exception:
            return default
    return default


def get_api_key():
    return get_secret("OPENAI_API_KEY")


def get_model(default_model: str) -> str:
    return get_secret("OPENAI_MODEL", default_model) or default_model


def get_fallback_model() -> str | None:
    return get_secret("OPENAI_FALLBACK_MODEL")


def is_mock_mode():
    return get_api_key() is None


def call_openai(system: str, user_message: str, model: str, max_tokens: int = 2000,
                mock_response: dict | None = None):
    """
    system/user_message로 OpenAI Responses API를 호출하고 JSON을 파싱해 반환한다.
    키가 없으면 mock_response를 그대로 반환한다(테스트/개발용).
    """
    if is_mock_mode():
        if mock_response is None:
            raise RuntimeError(
                "OPENAI_API_KEY가 설정되지 않았고 mock_response도 제공되지 않았습니다. "
                "실제 배포 전 반드시 API 키를 설정하세요."
            )
        return {"mock": True, **mock_response}

    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        BadRequestError,
        OpenAI,
        RateLimitError,
    )

    client = OpenAI(api_key=get_api_key())
    active_model = get_model(model)
    fallback_model = get_fallback_model()

    active_user_message = user_message
    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            resp = client.responses.create(
                model=active_model,
                instructions=system,
                input=[{"role": "user", "content": active_user_message}],
                text={"format": {"type": "json_object"}},
                max_output_tokens=max_tokens,
            )
            raw_text = getattr(resp, "output_text", "") or ""
            if not raw_text:
                raise RuntimeError("OpenAI 응답에서 output_text를 찾지 못했습니다.")
            parsed = _extract_json(raw_text)
            return {"mock": False, **parsed}
        except JSONExtractionError as e:
            if attempt == DEFAULT_MAX_RETRIES - 1:
                raise
            active_user_message = (
                f"{user_message}\n\n"
                "<RETRY_INSTRUCTION>\n"
                "이전 응답은 JSON 파싱에 실패했습니다. 같은 스키마로 다시 작성하되 "
                "반드시 완전한 JSON 객체 하나만 반환하세요. 문자열 값 안에는 실제 줄바꿈, "
                "이스케이프되지 않은 큰따옴표, 마크다운 코드블록을 넣지 마세요. "
                "긴 설명은 1~2문장으로 줄이고 표 셀 하나에는 한 줄 텍스트만 넣으세요.\n"
                f"이전 파싱 오류: {str(e)[:500]}\n"
                "</RETRY_INSTRUCTION>"
            )
            time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
        except BadRequestError as e:
            if fallback_model and _is_capacity_error(e) and active_model != fallback_model:
                active_model = fallback_model
                continue
            raise
        except (APIConnectionError, APIError, APITimeoutError, RateLimitError) as e:
            if fallback_model and _is_capacity_error(e) and active_model != fallback_model:
                active_model = fallback_model
                continue
            if attempt == DEFAULT_MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

    raise RuntimeError("OpenAI API 호출에 실패했습니다.")


def _is_capacity_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "capacity" in message
        or "overloaded" in message
        or "temporarily unavailable" in message
    )


def _extract_json(raw_text: str) -> dict:
    """
    모델 응답에서 JSON 객체를 견고하게 추출한다.
    """
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    start = raw_text.find("{")
    if start == -1:
        raise JSONExtractionError(f"응답에서 JSON 시작 '{{'를 찾지 못했습니다. 응답 앞부분: {raw_text[:300]!r}")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(raw_text)):
        ch = raw_text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = raw_text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as e:
                    raise JSONExtractionError(
                        f"괄호는 맞았지만 JSON 파싱에 실패했습니다: {e}\n"
                        f"추출한 텍스트 앞부분: {candidate[:300]!r}"
                    )
    raise JSONExtractionError(
        f"JSON 괄호가 끝까지 닫히지 않았습니다. 응답 마지막 부분: {raw_text[-300:]!r}"
    )
