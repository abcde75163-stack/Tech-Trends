# -*- coding: utf-8 -*-
"""
Call 2~6: STEP4~5 챕터별 본문 생성 오케스트레이션.
순차 실행 원칙 (설계 근거는 prompts/call2_6_design.md 참조):
  - Call6은 Call4 결과(cross_analysis)를 반드시 참조해야 하므로 Call4 이후에만 실행 가능
  - Phase 1은 단순성을 위해 전체 순차 실행
"""
import json
from pathlib import Path
from core.openai_client import call_openai, is_mock_mode
import config

_SCHEMAS = {
    "call2": """{
  "ch1": {"intro": "...", "background": "...", "kpi": [["지표","설명"]], "classification_desc": [["분류","범위"]]},
  "ch2": {"market_intro": "...", "policy": [["국가","정책동향"]], "players": [["기업명","역할","동향"]],
          "market_sources": [["출처/검색경로","확인할 항목","근거등급","비고"]],
          "market_confidence": "시장 수치의 근거 수준과 한계를 2~3문장으로",
          "chart5_market_data": {"sources": ["..."], "size_2030": [0], "cagr": [0]},
          "chart6_positioning_data": {"companies": {"기업명": [50, 50, 1000]}}}
}""",
    "call3": """{
  "ch3": {"overview": "...", "counts": [["분류","건수(E)"]],
          "chart4_country_data": {"years": [0], "countries": {"한국": [0]}, "share": {"한국": 0}},
          "applicants": [["출원인","건수동향","국가","영역"]], "ipc": [["코드","의미"]],
          "patent_search_strategy": {
            "core_keywords": ["..."],
            "ipc_cpc_candidates": [["코드","선정근거"]],
            "search_queries": [["검색원","검색식","검증링크","근거등급"]],
            "verification_note": "API/검색결과 파일이 없을 때 특허 정량값을 어떻게 해석해야 하는지"
          }},
  "ch4": {"summary": [["분류","원리","계보","응용"]]}
}""",
    "call4": """{
  "ch5": {"chart1_trend_data": {"years": [0], "areas": {"A": [0]}},
          "trends": ["..."], "by_area": {"A": "...", "B": "...", "C": "...", "D": "..."},
          "research_groups": [["유형","매체","성과"]],
          "chart2_keywords_data": {"keywords": ["..."], "period_a": [0], "period_b": [0]},
          "chart3_matrix_data": {"areas": ["..."], "rd_growth": [0], "patent_maturity": [0], "size": [0]},
          "cross_analysis": [["영역","R&D성장","특허성숙","전략"]]}
}""",
    "call5": """{
  "ch6": {"stages": [["분류","단계","R&D성장도","시사점"]], "overall": "..."},
  "ch7": {"history": [["출원인","시기별변화","전환패턴"]], "own_ip_note": "..."}
}""",
    "call6": """{
  "ch8": {"gaps": [["No","공백기술명","선행특허","신규IP안","진입가능성"]], "reorg_strategy": [["관점","전략내용"]]},
  "ch9": {"key_points": ["..."], "tasks": [["시점","과제명","구체행동"]], "limitations": ["..."],
          "evidence_grade": [["분석영역","근거등급","현재 근거","추가 검증 방법"]]}
}""",
}

CALL_LABELS = {
    "call2": "Ⅰ장(기술개요) + Ⅱ장(시장환경)",
    "call3": "Ⅲ장(특허정량) + Ⅳ장(핵심기술개요)",
    "call4": "Ⅴ장(R&D동향)",
    "call5": "Ⅵ장(성장단계) + Ⅶ장(IP히스토리)",
    "call6": "Ⅷ장(공백기술) + Ⅸ장(결론)",
}
CALL_ORDER = ["call2", "call3", "call4", "call5", "call6"]

# 호출별 max_tokens 차등 적용 (Ⅴ장은 차트3종+테이블2종+서술4개로 분량이 가장 많음)
CALL_MAX_TOKENS = {
    "call2": 6000,
    "call3": 6000,
    "call4": 12000,
    "call5": 6000,
    "call6": 7000,
}


def _load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_system_prompt(call_id: str) -> str:
    guide = _load(config.GUIDE_PATH)
    template = _load(config.TEMPLATE_PATH)
    return f"""당신은 "기술동향 분석 보고서 자동생성 시스템"의 챕터 본문 생성 모듈이다.
아래 두 문서가 유일한 행동 기준이다.

<GUIDE>
{guide}
</GUIDE>

<TEMPLATE>
{template}
</TEMPLATE>

## 임무
<CONFIRMED_CONTEXT>에 명시된 시나리오·기술분류를 기준으로 {CALL_LABELS[call_id]}의 본문을 작성한다.
GUIDE 4장(콘텐츠 작성 품질 기준)의 전문가 수준 서술, 추정치 (E) 표시 원칙을 반드시 따른다.
<CONFIRMED_CONTEXT>의 research_plan은 무료 공개 검색 기반 검증 경로다. 외부 API나 실제 검색결과 파일이 없으면 특허 건수·시장규모·기업 순위를 확정 사실처럼 쓰지 말고, 추정치(E)와 근거등급 C/D를 명시한다.
업로드된 특허/논문 검색결과 파일이 없는 경우 특허 정량 분석은 "검증 전 후보 분석"으로 작성하고, patent_search_strategy에 검색식과 검증 링크를 반드시 포함한다.
시장규모는 무료 공개자료만 가정할 때 단일 확정값보다 출처별 후보/범위/검증 필요성을 우선한다.
반드시 아래 JSON 스키마로만 응답한다. 다른 설명은 포함하지 않는다.

## 객관성 및 검증 수준 규칙
- 원자료 CSV/Excel 또는 실제 API 집계가 없으면 특허 건수, 논문 건수, 시장규모, CAGR, 기업 순위를 확정 사실처럼 쓰지 않는다.
- 추정 수치에는 반드시 (E)를 붙이고, 문장 안에 '후보', '추정', '검증 필요', '공개자료 기준' 중 하나를 포함한다.
- 시장규모는 단일 확정값이 아니라 출처별 후보값 또는 범위로 설명한다. chart5_market_data의 숫자는 차트 표시용 대표 후보값임을 market_confidence에 명시한다.
- market_sources에는 실제 원문 인용이 확인되지 않은 경우 '출처 후보' 또는 '검색 경로'라고 표시한다.
- 연구그룹, 기업, 출원인, 정책 동향은 실제로 널리 알려진 공개 정보 범위에서만 작성하고, 불확실하면 (E,C/D)로 낮은 근거등급을 표시한다.
- 표의 첫 번째 데이터 행에 헤더 예시(예: 분류/단계/시사점, 유형/매체/성과, 출원인/시기별변화/전환패턴)를 반복해서 넣지 않는다.
- 선행특허·FTO·공백기술은 법적 판단이 아니라 후보 스크리닝으로 표현하고, 전문 검토 필요성을 한계에 포함한다.

## JSON 안정성 규칙
- 응답은 완전한 JSON 객체 하나여야 하며, 마지막 중괄호까지 반드시 닫는다.
- 문자열 값 안에 실제 줄바꿈을 넣지 않는다. 긴 문장은 한 줄의 1~2문장으로 줄인다.
- 문자열 값 안에서 큰따옴표(")를 쓰지 않는다. 강조가 필요하면 작은따옴표(') 또는 괄호를 사용한다.
- 표 배열의 각 셀에는 줄바꿈 없는 짧은 텍스트만 넣는다.
- 마크다운 코드블록, 주석, JSON 바깥 설명은 절대 포함하지 않는다.

## 출력 스키마
{_SCHEMAS[call_id]}
"""


def build_user_message(confirmed_context: dict, prior_results: dict) -> str:
    parts = ["<CONFIRMED_CONTEXT>"]
    for k, v in confirmed_context.items():
        parts.append(f"{k}: {json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}")
    parts.append("</CONFIRMED_CONTEXT>")
    if prior_results.get("call4"):
        parts.append("\n<CALL4_RESULT_FOR_REFERENCE>")
        parts.append(json.dumps(prior_results["call4"], ensure_ascii=False))
        parts.append("</CALL4_RESULT_FOR_REFERENCE>")
    return "\n".join(parts)


def _mock_for(call_id: str, confirmed_context: dict) -> dict:
    """MOCK 모드 전용 — 구조 검증용 placeholder. 실제 도메인 콘텐츠 아님."""
    tech = confirmed_context.get("tech_name", "기술명")
    if call_id == "call2":
        return {
            "ch1": {"intro": f"[MOCK] {tech} 개요", "background": "[MOCK] 배경 설명",
                    "kpi": [["지표1", "설명1"]], "classification_desc": [["A", "범위"]]},
            "ch2": {"market_intro": "[MOCK] 시장 개요", "policy": [["한국", "정책(E)"]],
                    "players": [["기업A", "역할", "동향"]],
                    "market_sources": [["공개 웹/IR 검색", "시장규모·CAGR 후보 확인", "C", "실제 보고서에서는 출처별 비교 필요"]],
                    "market_confidence": "MOCK 기준 시장 수치는 검증 전 추정치이며 공개자료 확인이 필요합니다.",
                    "chart5_market_data": {"sources": ["출처1(E)"], "size_2030": [40], "cagr": [20]},
                    "chart6_positioning_data": {"companies": {"기업A": [50, 50, 1000]}}},
        }
    if call_id == "call3":
        return {
            "ch3": {"overview": "[MOCK] 특허 개요", "counts": [["A", "100건(E)"]],
                    "chart4_country_data": {"years": [2024, 2025], "countries": {"한국": [10, 20]}, "share": {"한국": 50}},
                    "applicants": [["기업A", "증가", "한국", "영역"]], "ipc": [["H01L", "의미"]],
                    "patent_search_strategy": {
                        "core_keywords": [tech, "keyword"],
                        "ipc_cpc_candidates": [["H01L", "MOCK 후보"]],
                        "search_queries": [["Google Patents", tech, "https://patents.google.com/", "C"]],
                        "verification_note": "MOCK 정량값은 검증 전 후보값입니다."
                    }},
            "ch4": {"summary": [["A", "원리", "계보", "응용"]]},
        }
    if call_id == "call4":
        return {"ch5": {
            "chart1_trend_data": {"years": [2024, 2025], "areas": {"A": [10, 20]}},
            "trends": ["[MOCK] 트렌드1"], "by_area": {"A": "...", "B": "...", "C": "...", "D": "..."},
            "research_groups": [["유형", "매체", "성과"]],
            "chart2_keywords_data": {"keywords": ["키워드1"], "period_a": [10], "period_b": [20]},
            "chart3_matrix_data": {"areas": ["A"], "rd_growth": [50], "patent_maturity": [50], "size": [1000]},
            "cross_analysis": [["A", "높음", "중간", "전략"]],
        }}
    if call_id == "call5":
        return {
            "ch6": {"stages": [["A", "성장기", "높음", "시사점"]], "overall": "[MOCK] 종합판단"},
            "ch7": {"history": [["기업A", "변화", "패턴"]], "own_ip_note": "[MOCK] 시나리오별 안내"},
        }
    if call_id == "call6":
        return {
            "ch8": {"gaps": [["1", "공백기술1", "선행특허", "신규안", "★★★☆☆"]],
                    "reorg_strategy": [["종류확장", "전략내용"]]},
            "ch9": {"key_points": ["[MOCK] 요약1"], "tasks": [["즉시", "과제", "행동"]],
                    "limitations": ["[MOCK] 한계1"],
                    "evidence_grade": [["특허", "D", "MOCK 추정", "검색결과 파일 업로드 후 재집계"]]},
        }
    raise ValueError(call_id)


def run_all_calls(confirmed_context: dict, model=config.DEFAULT_MODEL, progress_callback=None):
    """
    순차적으로 call2~call6을 실행한다.
    progress_callback(idx, total, label)이 주어지면 매 호출 전 호출한다.
    반환: {"call2": {...}, "call3": {...}, ...}
    """
    results = {}
    for i, call_id in enumerate(CALL_ORDER, start=1):
        if progress_callback:
            progress_callback(i, len(CALL_ORDER), CALL_LABELS[call_id])

        mock_response = _mock_for(call_id, confirmed_context) if is_mock_mode() else None
        system_prompt = build_system_prompt(call_id)
        user_message = build_user_message(confirmed_context, results)
        try:
            results[call_id] = call_openai(system_prompt, user_message, model=model,
                                            max_tokens=CALL_MAX_TOKENS[call_id], mock_response=mock_response)
        except Exception as e:
            raise RuntimeError(f"[{call_id} — {CALL_LABELS[call_id]}] 생성 실패: {e}") from e
    return results
