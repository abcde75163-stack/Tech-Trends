# -*- coding: utf-8 -*-
"""
Call 1: STEP1~3 (입력확인·시나리오판별·기술분류 제안) 오케스트레이션.
GUIDE_v2.1 / TEMPLATE_v2 파일을 그대로 읽어 프롬프트에 주입한다(하드코딩 금지 원칙).
"""
from pathlib import Path
from core.openai_client import call_openai, is_mock_mode
import config

_SYSTEM_TEMPLATE = """당신은 "기술동향 분석 보고서 자동생성 시스템"의 STEP1~3 담당 모듈이다.
아래 두 문서가 이 시스템의 유일한 행동 기준이다. 두 문서에 명시되지 않은 임의의 규칙을 만들어내지 않는다.

<GUIDE>
{guide}
</GUIDE>

<TEMPLATE>
{template}
</TEMPLATE>

## 임무
사용자가 입력한 정보를 바탕으로 GUIDE의 "2. 보고서 생성 시작 시 행동 순서 — STEP1~3"을 수행한다.

1. 기술명이 없으면 status를 "missing_tech_name"으로 반환한다.
2. GUIDE 1-2절 기준으로 시나리오(A/B/C)를 판별한다.
3. GUIDE 1-1절의 "세션/메모리 정보 자동 적용 금지" 원칙에 따라 <USER_INPUT>에 명시된 정보만 근거로 판단한다.
4. TEMPLATE "⚙️ 기술 분류 자동 조정 기준"에 따라 A~D 4개 기술 분류 체계 초안을 제안한다.
   - 기술명이 이차전지, 배터리, 전지, ESS, 리튬이온, 전고체, 양극재, 음극재, 전해질, 분리막 등 배터리 도메인을 가리키면
     field_type은 "소재·화학·배터리"로 우선 판별한다.
   - 배터리 도메인의 A~D 분류는 발전/저장/변환/시스템처럼 에너지 시스템 관점으로 나누지 말고,
     A 전극·전해질 소재, B 셀 설계·제조공정, C BMS·충방전 제어, D 팩·시스템·안전·재활용 관점으로 제안한다.
5. 반드시 아래 JSON 스키마로만 응답한다. JSON 외의 설명은 절대 포함하지 않는다.

## 출력 스키마
{{
  "status": "ok" | "missing_tech_name",
  "scenario": "A" | "B" | "C" | null,
  "scenario_reason": "판별 근거를 1~2문장으로",
  "field_type": "TEMPLATE의 6개 분야 유형 중 하나",
  "classification": [
    {{"code": "A", "name": "...", "scope": "..."}},
    {{"code": "B", "name": "...", "scope": "..."}},
    {{"code": "C", "name": "...", "scope": "..."}},
    {{"code": "D", "name": "...", "scope": "..."}}
  ],
  "confirmation_message": "사용자에게 보여줄 한 번의 확인 메시지"
}}
"""


def _load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_system_prompt() -> str:
    guide = _load(config.GUIDE_PATH)
    template = _load(config.TEMPLATE_PATH)
    return _SYSTEM_TEMPLATE.format(guide=guide, template=template)


def build_user_message(tech_name, org_name, has_capability, org_capability, attachment_summary, purpose) -> str:
    return (
        "<USER_INPUT>\n"
        f"기술명: {tech_name or '(미입력)'}\n"
        f"의뢰 기관명: {org_name or '없음'}\n"
        f"의뢰 기관 역량 정보 제공 여부: {'있음' if has_capability else '없음'}\n"
        f"의뢰 기관 역량/사업 영역: {org_capability if has_capability else '없음'}\n"
        f"첨부파일: {attachment_summary or '없음'}\n"
        f"분석 목적: {purpose or f'명시 안 됨 (기본값: {config.DEFAULT_PURPOSE} 적용)'}\n"
        "</USER_INPUT>"
    )


def _local_scenario_rule(org_name, has_capability):
    """UI 목업(MOCK) 전용 — 실제 시나리오 판별 로직이 아니라 화면 흐름 테스트용 근사치."""
    if not org_name:
        return "A", "의뢰 기관명이 입력되지 않아 시나리오 A로 판별 (MOCK 근사)"
    if has_capability:
        return "B", "의뢰 기관명과 역량 정보가 모두 제공되어 시나리오 B로 판별 (MOCK 근사)"
    return "C", "의뢰 기관명은 있으나 역량 정보가 없어 시나리오 C로 판별 (MOCK 근사)"


def run_call1(tech_name, org_name, has_capability, org_capability, attachment_summary, purpose,
              model=config.DEFAULT_MODEL):
    if not tech_name:
        return {"status": "missing_tech_name", "scenario": None, "scenario_reason": "",
                "field_type": None, "classification": [],
                "confirmation_message": "기술명을 입력해주세요.", "mock": is_mock_mode()}

    mock_response = None
    if is_mock_mode():
        scenario, reason = _local_scenario_rule(org_name, has_capability)
        mock_response = {
            "status": "ok",
            "scenario": scenario,
            "scenario_reason": reason,
            "field_type": "(MOCK) 실제 API 연결 전 임시값 — 분야 자동판별 미실행",
            "classification": [
                {"code": "A", "name": f"[MOCK] {tech_name} 분류 A", "scope": "실제 API 연결 후 자동 생성 예정"},
                {"code": "B", "name": f"[MOCK] {tech_name} 분류 B", "scope": "실제 API 연결 후 자동 생성 예정"},
                {"code": "C", "name": f"[MOCK] {tech_name} 분류 C", "scope": "실제 API 연결 후 자동 생성 예정"},
                {"code": "D", "name": f"[MOCK] {tech_name} 분류 D", "scope": "실제 API 연결 후 자동 생성 예정"},
            ],
            "confirmation_message": (
                f"[MOCK 응답] {config.SCENARIO_LABELS[scenario]} 기준으로 진행 예정입니다. "
                f"(실제 API 키 연결 전이므로 분류 내용은 자리표시자입니다)"
            ),
        }

    system_prompt = build_system_prompt()
    user_message = build_user_message(tech_name, org_name, has_capability, org_capability,
                                       attachment_summary, purpose)
    return call_openai(system_prompt, user_message, model=model, mock_response=mock_response)
