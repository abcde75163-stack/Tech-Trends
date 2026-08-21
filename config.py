# -*- coding: utf-8 -*-
"""앱 전역 설정값. GUIDE_v2.1 / TEMPLATE_v2 기준값과 동기화."""

APP_TITLE = "기술동향 분석 보고서 자동생성"
DEFAULT_MODEL = "gpt-5"
DEFAULT_PURPOSE = "내부 검토용"

# 색상 (GUIDE_v2.1 섹션 6 기준)
PRIMARY_COLOR = "#1F4E79"
SECONDARY_COLOR = "#2E75B6"
LIGHT_ROW_COLOR = "#EBF3FA"

GUIDE_PATH = "guide/REPORT_GUIDE_v2.1.md"
TEMPLATE_PATH = "guide/REPORT_TEMPLATE_v2.md"

SCENARIO_LABELS = {
    "A": "시나리오 A — 기술동향 분석만 (기업 무관)",
    "B": "시나리오 B — 기술동향 분석 + 특정 기업 IP 전략 연계",
    "C": "시나리오 C — 기술동향 분석 + 공백기술 제안 (기업명만 제공)",
}

# Phase 1 운영 정책 (기획서 8절 반영)
AUTH_ENABLED = False          # Phase 2에서 True로 전환 예정
DEFAULT_USER_ID = "default_user"   # 추후 로그인 도입 시 실제 user_id로 대체
