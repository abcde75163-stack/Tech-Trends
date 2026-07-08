# Call 2~6 시스템 프롬프트 설계 (STEP4~5: 챕터별 본문 생성)

> Call 1에서 확정된 시나리오·기술분류를 입력으로 받아 챕터별 본문을 생성한다.
> 기획서(streamlit_plan.md) 5절의 호출 그룹핑을 그대로 따른다.
> GUIDE_v2.1 / TEMPLATE_v2 전문은 Call 1과 동일하게 매 호출 system prompt에 포함한다
> (로직 하드코딩 금지 원칙 — 두 파일이 수정되면 모든 Call이 자동으로 갱신된 규칙을 따름).

---

## 공통 입력 (모든 Call 2~6에 전달)

```
<CONFIRMED_CONTEXT>
기술명: {tech_name}
시나리오: {scenario}  (A/B/C)
의뢰 기관명: {org_name | "없음"}
의뢰 기관 역량: {org_capability | "없음"}
기술 분류(A~D 확정본): {classification_json}
분석 목적: {purpose}
첨부 데이터 유무: 특허데이터={has_patent_data}, 논문데이터={has_paper_data}
</CONFIRMED_CONTEXT>
```

## 공통 출력 규칙
- 반드시 JSON만 반환 (설명 텍스트 금지)
- 시장 규모·특허 건수 등 추정치는 값 자체에 "(E)" 포함
- 시나리오별 관점 차이(GUIDE 1-2절)를 각 챕터 서술에 반영
- 표 형태 콘텐츠는 `rows: [[...], [...]]` 배열로, 차트가 필요한 챕터는 `chart_data` 필드에 matplotlib에서 바로 쓸 수 있는 구조화 수치 포함
- JSON 문자열 값 내부에는 큰따옴표(")를 절대 사용하지 않는다. 강조·인용이 필요한 경우 작은따옴표(') 또는 「」를 사용한다.

   잘못된 예: "overview": "유효 특허 \"15,000여 건\"으로 추정"
   올바른 예: "overview": "유효 특허 '15,000여 건'으로 추정" 또는 "overview": "유효 특허 「15,000여 건」으로 추정"

- 숫자·단위를 강조할 때도 따옴표 대신 괄호나 별표를 사용한다 (예: 약 15,000건(추정) 또는 **15,000건** 금지 시 그냥 괄호 사용).
---

## Call 2 — Ⅰ장(기술개요) + Ⅱ장(시장환경)

**추가 입력**: 없음 (공통 입력으로 충분)

**출력 스키마**
```json
{
  "ch1": {
    "intro": "...", "background": "...",
    "kpi": [["지표", "설명"], ...],
    "classification_desc": [["분류", "범위"], ...]
  },
  "ch2": {
    "market_intro": "...",
    "policy": [["국가", "정책동향"], ...],
    "players": [["기업명", "역할", "동향"], ...],
    "chart5_market_data": {"sources": [...], "size_2030": [...], "cagr": [...]},
    "chart6_positioning_data": {"companies": {"name": [x, y, size], ...}}
  }
}
```

## Call 3 — Ⅲ장(특허정량) + Ⅳ장(핵심기술개요)

**출력 스키마**
```json
{
  "ch3": {
    "overview": "...",
    "counts": [["분류", "추정건수"], ...],
    "chart4_country_data": {"years": [...], "countries": {"한국": [...], ...}, "share": {...}},
    "applicants": [["출원인", "건수동향", "국가", "영역"], ...],
    "ipc": [["코드", "의미"], ...]
  },
  "ch4": {
    "summary": [["분류", "원리", "계보", "응용"], ...]
  }
}
```

## Call 4 — Ⅴ장(R&D동향) — 단독 호출 (분량 최다)

**출력 스키마**
```json
{
  "ch5": {
    "chart1_trend_data": {"years": [...], "areas": {"A분류명": [...], ...}},
    "trends": ["...", "..."],
    "by_area": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "research_groups": [["유형", "매체", "성과"], ...],
    "chart2_keywords_data": {"keywords": [...], "period_a": [...], "period_b": [...]},
    "chart3_matrix_data": {"areas": [...], "rd_growth": [...], "patent_maturity": [...], "size": [...]},
    "cross_analysis": [["영역", "R&D성장", "특허성숙", "전략"], ...]
  }
}
```
※ Ⅷ장 공백기술은 이 Call4의 `cross_analysis` 결과와 연동해야 하므로, Call6 호출 시 Call4 결과를 함께 프롬프트에 포함한다.

## Call 5 — Ⅵ장(성장단계) + Ⅶ장(IP히스토리)

**출력 스키마**
```json
{
  "ch6": {"stages": [["분류","단계","R&D성장도","시사점"], ...], "overall": "..."},
  "ch7": {
    "history": [["출원인", "시기별변화", "전환패턴"], ...],
    "own_ip_note": "시나리오별 분기 서술 (A: 해당없음 / B: 보유IP현황 / C: 확인필요 안내)"
  }
}
```

## Call 6 — Ⅷ장(공백기술) + Ⅸ장(결론) — Call4 결과 참조 필수

**추가 입력**: Call4의 `cross_analysis`, `chart3_matrix_data` 결과를 프롬프트에 포함

**출력 스키마**
```json
{
  "ch8": {
    "gaps": [["No","공백기술명","선행특허","신규IP안","진입가능성"], ...],
    "reorg_strategy": [["관점","전략내용"], ...]
  },
  "ch9": {
    "key_points": ["...", ...],
    "tasks": [["시점","과제명","구체행동"], ...],
    "limitations": ["...", ...]
  }
}
```

---

## 설계 시 발견한 이슈 (self-check)

1. **Call4→Call6 의존성**: Call6은 Call4의 결과를 반드시 참조해야 하므로 순차 실행이 강제된다. Call2/3/5는 서로 독립적이라 이론적으로는 병렬화가 가능하지만, Call5(Ⅶ장 own_ip_note)가 시나리오 B일 때 Call2에서 다루는 시장 내 기업 동향과 톤이 어긋나지 않으려면 결국 순차 실행이 안전하다. → **Phase 1은 순차 실행으로 단순하게 간다.**
2. **차트 데이터 형식 불일치 리스크**: 각 Call이 반환하는 `chart*_data`가 matplotlib 스크립트가 기대하는 키 이름과 정확히 일치해야 한다. 모델이 매번 완전히 동일한 키 이름으로 반환한다는 보장이 없으므로, `chart_generator.py`에서 각 차트별로 필수 키 존재 여부를 검증하고 누락 시 명확한 에러를 던지는 방어 코드가 필요하다 (다음 단계 구현 시 반영 필요).
