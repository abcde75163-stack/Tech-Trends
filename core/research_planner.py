# -*- coding: utf-8 -*-
"""무료 공개 검색 기반 조사 계획과 검증 링크를 생성한다."""
from __future__ import annotations

from urllib.parse import quote_plus


def build_research_plan(tech_name: str, classification=None, attachment_summary: str | None = None) -> dict:
    tech = (tech_name or "").strip()
    class_terms = []
    for item in classification or []:
        if isinstance(item, dict):
            class_terms.extend([item.get("name", ""), item.get("scope", "")])
        else:
            class_terms.append(str(item))
    class_terms = [t.strip() for t in class_terms if t and str(t).strip()]

    base_terms = [tech] + class_terms[:4]
    query_ko = " ".join(t for t in base_terms if t) or tech
    query_en = tech
    if any(ord(ch) > 127 for ch in tech):
        query_en = f"{tech} technology patent market research"

    patent_query = f'"{tech}" OR ({query_en})' if tech else query_en
    paper_query = f'{tech} {query_en} research trend'
    market_query = f'{tech} {query_en} market size CAGR policy company IR'

    has_attachment = bool(attachment_summary and attachment_summary.strip())
    evidence_grade = "C" if has_attachment else "D"
    evidence_reason = (
        "업로드 기술문서 요약을 기반으로 검색식과 분석 가설을 생성함"
        if has_attachment else
        "기술명과 사용자 입력만으로 검색식과 분석 가설을 생성함"
    )

    return {
        "input_basis": {
            "grade": evidence_grade,
            "reason": evidence_reason,
            "note": "외부 유료 특허 DB 없이 무료 공개 검색으로 검증 가능한 조사 경로를 제시합니다.",
        },
        "search_terms": {
            "korean": query_ko,
            "english": query_en,
            "patent_query": patent_query,
            "paper_query": paper_query,
            "market_query": market_query,
        },
        "patent_search_links": [
            {
                "source": "KIPRIS",
                "purpose": "국내 특허/실용신안 검색",
                "url": "https://www.kipris.or.kr/khome/main.do",
                "query": query_ko,
                "grade": "C",
                "note": "공식 검색 화면에서 검색식 확인 후 결과 파일을 내려받으면 A등급 집계로 전환 가능",
            },
            {
                "source": "Google Patents",
                "purpose": "글로벌 특허/비특허문헌 후보 탐색",
                "url": f"https://patents.google.com/?q={quote_plus(patent_query)}",
                "query": patent_query,
                "grade": "C",
                "note": "무료 검색 링크 기반 후보 탐색. 대량 정량값은 검증 필요",
            },
            {
                "source": "Espacenet",
                "purpose": "EPO 기반 글로벌 특허 패밀리 탐색",
                "url": f"https://worldwide.espacenet.com/patent/search?q={quote_plus(patent_query)}",
                "query": patent_query,
                "grade": "C",
                "note": "검색 결과 수와 패밀리 정보는 화면 기준으로 재확인 필요",
            },
            {
                "source": "The Lens",
                "purpose": "특허/논문 교차 탐색",
                "url": f"https://www.lens.org/lens/search/patent/list?q={quote_plus(patent_query)}",
                "query": patent_query,
                "grade": "C",
                "note": "웹 검색은 가능하나 API 자동화는 요금/권한 제한 확인 필요",
            },
        ],
        "scholar_search_links": [
            {
                "source": "OpenAlex",
                "purpose": "논문/R&D 메타데이터 자동 조회 후보",
                "url": f"https://api.openalex.org/works?search={quote_plus(paper_query)}&per-page=25",
                "query": paper_query,
                "grade": "B",
                "note": "무료 키 또는 제한 범위에서 자동 조회 가능. 결과는 메타데이터 기준",
            },
            {
                "source": "Crossref",
                "purpose": "DOI 기반 논문/보고서 메타데이터 보조 조회",
                "url": f"https://api.crossref.org/works?query={quote_plus(paper_query)}&rows=20",
                "query": paper_query,
                "grade": "B",
                "note": "가입 없이 공개 메타데이터 조회 가능",
            },
        ],
        "market_search_links": [
            {
                "source": "Public Web",
                "purpose": "시장규모/CAGR/정책/기업 IR 공개자료 탐색",
                "url": f"https://www.google.com/search?q={quote_plus(market_query)}",
                "query": market_query,
                "grade": "C",
                "note": "무료 공개자료 기반. 수치는 단일값보다 범위와 출처별 비교로 제시",
            },
            {
                "source": "Google Scholar",
                "purpose": "시장·기술 리뷰 논문/보고서 후보 탐색",
                "url": f"https://scholar.google.com/scholar?q={quote_plus(paper_query)}",
                "query": paper_query,
                "grade": "C",
                "note": "접근 가능한 원문 여부와 최신성 확인 필요",
            },
        ],
        "evidence_grades": [
            ["A", "사용자 업로드 검색결과 파일 직접 집계", "특허/논문 CSV·Excel 등 원자료가 있는 경우"],
            ["B", "무료 공개 API 직접 조회", "OpenAlex, Crossref 등 메타데이터 API 기반"],
            ["C", "공개 검색 링크/웹자료 기반", "KIPRIS, Google Patents, Espacenet, IR/보도자료 등"],
            ["D", "AI 추정", "검증 데이터가 부족해 가설 수준으로만 사용"],
        ],
    }
