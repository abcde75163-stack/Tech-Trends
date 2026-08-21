# -*- coding: utf-8 -*-
"""
차트 생성 모듈. Call2~6이 반환한 chart_*_data를 matplotlib으로 렌더링한다.
GUIDE_v2.1 섹션 5의 폴백 폰트 탐색 원칙을 따르되, Streamlit Cloud 배포를 고려해
리포지토리에 번들된 서브셋 폰트를 최우선으로 사용한다(기획서 6절 반영).

방어적 설계: 각 차트 함수는 필요한 키가 없으면 즉시 명확한 에러를 발생시킨다.
(report_generator.py 설계 문서에서 미리 지적한 "차트 데이터 키 불일치 리스크" 대응)
"""
import os
import io
from pathlib import Path
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

APP_DIR = Path(__file__).resolve().parent.parent

FONT_CANDIDATES = [
    str(APP_DIR / "assets" / "fonts" / "NotoSansKR-subset.otf"),  # 1순위: 리포지토리 번들 폰트
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
COLORS = ['#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#e34948', '#eb6834']


class ChartDataError(ValueError):
    """chart_*_data에 필요한 키가 없을 때 발생시키는 예외."""


def _get_font_prop(size=11):
    font_path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if font_path is None:
        raise RuntimeError("사용 가능한 한글 폰트를 찾지 못함 — assets/fonts에 폰트 파일이 있는지 확인 필요")
    fm.fontManager.addfont(font_path)
    return fm.FontProperties(fname=font_path, size=size), font_path


def _require_keys(data: dict, keys: list, chart_name: str):
    missing = [k for k in keys if k not in data]
    if missing:
        raise ChartDataError(f"{chart_name}: 필수 키 누락 {missing} (받은 키: {list(data.keys())})")


def _style_axes(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, color='#EBEBEB', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def _to_buffer(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    buf.seek(0)
    return buf


def chart1_trend(data: dict) -> io.BytesIO:
    _require_keys(data, ["years", "areas"], "chart1_trend_data")
    fp, _ = _get_font_prop(13)
    fp_s, _ = _get_font_prop(9)
    years = data["years"]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for i, (name, values) in enumerate(data["areas"].items()):
        ax.plot(years, values, marker='o', linewidth=2.2, color=COLORS[i % len(COLORS)], label=name)
    _style_axes(ax)
    ax.set_title('기술 영역별 연도별 논문 건수 추이 (E)', fontproperties=fp)
    ax.set_xticks(years)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(fp_s)
    ax.legend(prop=fp_s, loc='upper left', frameon=False)
    return _to_buffer(fig)


def chart2_keywords(data: dict) -> io.BytesIO:
    _require_keys(data, ["keywords", "period_a", "period_b"], "chart2_keywords_data")
    fp, _ = _get_font_prop(13)
    fp_s, _ = _get_font_prop(9)
    import numpy as np
    x = np.arange(len(data["keywords"]))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.bar(x - width / 2, data["period_a"], width, color=COLORS[0], label='이전 기간')
    ax.bar(x + width / 2, data["period_b"], width, color=COLORS[4], label='최근 기간(E)')
    _style_axes(ax)
    ax.set_title('핵심 키워드 출현 빈도 비교 (E)', fontproperties=fp)
    ax.set_xticks(x)
    ax.set_xticklabels(data["keywords"], fontproperties=fp_s)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(fp_s)
    ax.legend(prop=fp_s, frameon=False)
    return _to_buffer(fig)


def chart3_matrix(data: dict) -> io.BytesIO:
    _require_keys(data, ["areas", "rd_growth", "patent_maturity", "size"], "chart3_matrix_data")
    fp, _ = _get_font_prop(13)
    fp_s, _ = _get_font_prop(9)
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    for i, area in enumerate(data["areas"]):
        ax.scatter(data["patent_maturity"][i], data["rd_growth"][i], s=data["size"][i],
                   color=COLORS[i % len(COLORS)], alpha=0.55, edgecolors=COLORS[i % len(COLORS)], linewidths=1.5)
        ax.annotate(area, (data["patent_maturity"][i], data["rd_growth"][i]), fontproperties=fp_s,
                    ha='center', va='center')
    ax.axvline(55, color='#BBBBBB', linewidth=1, linestyle='--')
    ax.axhline(55, color='#BBBBBB', linewidth=1, linestyle='--')
    _style_axes(ax)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel('특허 성숙도 (지수)', fontproperties=fp)
    ax.set_ylabel('R&D 성장도 (지수)', fontproperties=fp)
    ax.set_title('R&D-특허 포지셔닝 매트릭스 (E)', fontproperties=fp)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(fp_s)
    return _to_buffer(fig)


def chart4_country(data: dict) -> io.BytesIO:
    _require_keys(data, ["years", "countries", "share"], "chart4_country_data")
    fp, _ = _get_font_prop(12)
    fp_s, _ = _get_font_prop(9)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), gridspec_kw={'width_ratios': [1.5, 1]})
    ax = axes[0]
    for i, (country, values) in enumerate(data["countries"].items()):
        ax.plot(data["years"], values, marker='o', linewidth=2, color=COLORS[i % len(COLORS)], label=country)
    _style_axes(ax)
    ax.set_title('국가별 연도별 특허 출원 추이 (E)', fontproperties=fp)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(fp_s)
    ax.legend(prop=fp_s, frameon=False, ncol=2)

    ax2 = axes[1]
    items = sorted(data["share"].items(), key=lambda x: x[1])
    names = [x[0] for x in items]; vals = [x[1] for x in items]
    ax2.barh(names, vals, color=COLORS[1])
    for i, v in enumerate(vals):
        ax2.text(v + 0.5, i, f'{v}%', va='center', fontproperties=fp_s)
    _style_axes(ax2)
    ax2.set_title('누적 출원 비중 (E)', fontproperties=fp)
    for lbl in ax2.get_yticklabels() + ax2.get_xticklabels():
        lbl.set_fontproperties(fp_s)
    fig.tight_layout()
    return _to_buffer(fig)


def chart5_market(data: dict) -> io.BytesIO:
    _require_keys(data, ["sources", "size_2030", "cagr"], "chart5_market_data")
    fp, _ = _get_font_prop(12)
    fp_s, _ = _get_font_prop(9)
    import numpy as np
    y_pos = np.arange(len(data["sources"]))
    fig, ax1 = plt.subplots(figsize=(9, 5.2))
    ax1.barh(y_pos, data["size_2030"], color=COLORS[0], alpha=0.85, label='시장규모 전망')
    ax1.set_yticks(y_pos); ax1.set_yticklabels(data["sources"], fontproperties=fp_s)
    for lbl in ax1.get_xticklabels():
        lbl.set_fontproperties(fp_s)
    _style_axes(ax1)
    ax2 = ax1.twiny()
    ax2.scatter(data["cagr"], y_pos, color=COLORS[4], s=110, zorder=5, label="CAGR(%)")
    for lbl in ax2.get_xticklabels():
        lbl.set_fontproperties(fp_s)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, prop=fp_s, loc='lower right', frameon=False)
    ax1.set_title('출처별 시장 규모·CAGR 전망 비교 (E)', fontproperties=fp, pad=40)
    fig.tight_layout()
    return _to_buffer(fig)


def chart6_positioning(data: dict) -> io.BytesIO:
    _require_keys(data, ["companies"], "chart6_positioning_data")
    fp, _ = _get_font_prop(13)
    fp_s, _ = _get_font_prop(9)
    fig, ax = plt.subplots(figsize=(9, 6.5))
    for i, (name, (x, y, s)) in enumerate(data["companies"].items()):
        c = COLORS[i % len(COLORS)]
        ax.scatter(x, y, s=s, color=c, alpha=0.6, edgecolors=c, linewidths=1.5)
        ax.annotate(name, (x, y), fontproperties=fp_s, ha='center', va='center')
    ax.axvline(50, color='#BBBBBB', linewidth=1, linestyle='--')
    ax.axhline(50, color='#BBBBBB', linewidth=1, linestyle='--')
    _style_axes(ax)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel('소재·소자 중심 ↔ 시스템·플랫폼 중심', fontproperties=fp)
    ax.set_ylabel('부품 공급 ↔ 완제품·플랫폼 리더', fontproperties=fp)
    ax.set_title('주요 기업 포지셔닝 맵 (E)', fontproperties=fp)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(fp_s)
    return _to_buffer(fig)


def generate_all_charts(chapter_results: dict) -> dict:
    """
    chapter_results(Call2~6 결과)로부터 6개 차트를 생성해 {이름: BytesIO} 형태로 반환한다.
    키 누락 시 ChartDataError를 그대로 전파한다 — 호출부(app.py)에서 사용자에게 안내해야 한다.
    """
    ch2 = chapter_results["call2"]["ch2"]
    ch3 = chapter_results["call3"]["ch3"]
    ch5 = chapter_results["call4"]["ch5"]
    return {
        "chart1_trend": chart1_trend(ch5["chart1_trend_data"]),
        "chart2_keywords": chart2_keywords(ch5["chart2_keywords_data"]),
        "chart3_matrix": chart3_matrix(ch5["chart3_matrix_data"]),
        "chart4_country": chart4_country(ch3["chart4_country_data"]),
        "chart5_market": chart5_market(ch2["chart5_market_data"]),
        "chart6_positioning": chart6_positioning(ch2["chart6_positioning_data"]),
    }
