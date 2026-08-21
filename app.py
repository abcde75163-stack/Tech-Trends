# -*- coding: utf-8 -*-
"""
기술동향 분석 보고서 자동생성 — Streamlit 원클릭 UI
기술명 입력 후 시나리오 판별, 기술 분류, 챕터 생성, 차트 생성, Word 조립을 자동 진행한다.
"""
import streamlit as st
import config
from core.attachment_parser import build_attachment_summary
from core.research_planner import build_research_plan
from core.scenario_engine import run_call1
from core.openai_client import is_mock_mode

st.set_page_config(page_title=config.APP_TITLE, page_icon="📊", layout="centered")

if "step" not in st.session_state:
    st.session_state.step = "input"
if "call1_result" not in st.session_state:
    st.session_state.call1_result = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

st.title("📊 " + config.APP_TITLE)

if is_mock_mode():
    st.warning(
        "⚠️ OPENAI_API_KEY가 설정되어 있지 않아 **MOCK 모드**로 동작 중입니다. "
        "실제 시나리오 판별·기술 분류 대신 자리표시자가 표시됩니다. "
        "실제 배포 전 `.streamlit/secrets.toml`에 키를 등록하세요.",
        icon="⚠️",
    )

st.progress({"input": 0.15, "generate": 0.5}.get(st.session_state.step, 0.0))

# =================================================================
# 입력 화면: 기술명 입력 후 즉시 보고서 생성
# =================================================================
if st.session_state.step == "input":
    st.subheader("보고서 바로 생성")

    with st.form("input_form"):
        tech_name = st.text_input("기술명 *", placeholder="예: HBM (High Bandwidth Memory)")

        uploaded_files = st.file_uploader(
            "첨부파일 (특허 CSV/Excel, 논문 Excel, 특허 명세서 PDF 등)",
            accept_multiple_files=True,
        )

        purpose = st.selectbox(
            "분석 목적",
            ["내부 검토용", "TLO 기술이전", "외부 제출", "직접 입력"],
        )
        if purpose == "직접 입력":
            purpose = st.text_input("분석 목적 직접 입력", value="")

        with st.expander("고급 옵션: 의뢰 기관 정보 입력", expanded=False):
            st.caption("비워두면 기업 무관 범용 보고서(시나리오 A)로 자동 생성됩니다.")
            org_name = st.text_input("의뢰 기관명", placeholder="예: OO대학교 산학협력단")
            org_capability = st.text_area(
                "보유 역량/사업 영역 요약",
                placeholder="예: 광섬유 피복 소재 제조 역량 보유",
            )

        submitted = st.form_submit_button("보고서 바로 생성", type="primary", width='stretch')

    if submitted:
        attachment_summary = build_attachment_summary(uploaded_files)
        has_capability = bool(org_capability.strip())
        st.session_state.inputs = dict(
            tech_name=tech_name.strip(),
            org_name=org_name.strip() or None,
            has_capability=has_capability,
            org_capability=org_capability.strip() or None,
            attachment_summary=attachment_summary,
            purpose=purpose or None,
        )
        with st.spinner("시나리오 판별 및 기술 분류 제안 생성 중..."):
            try:
                result = run_call1(**st.session_state.inputs)
            except Exception as e:
                st.error(f"시나리오 판별 중 오류가 발생했습니다:\n\n{e}")
                st.stop()
        st.session_state.call1_result = result

        if result["status"] == "missing_tech_name":
            st.error(result["confirmation_message"])
        else:
            st.session_state.confirmed_classification = result["classification"]
            st.session_state.gen_error = None
            st.session_state.step = "generate"

            confirmed_context = dict(
                tech_name=st.session_state.inputs["tech_name"],
                scenario=result["scenario"],
                org_name=st.session_state.inputs["org_name"],
                org_capability=st.session_state.inputs["org_capability"],
                attachment_summary=st.session_state.inputs.get("attachment_summary"),
                classification=st.session_state.confirmed_classification,
                purpose=st.session_state.inputs["purpose"],
            )
            confirmed_context["research_plan"] = build_research_plan(
                confirmed_context["tech_name"],
                confirmed_context["classification"],
                confirmed_context.get("attachment_summary"),
            )

            st.info(f"자동 적용 시나리오: {config.SCENARIO_LABELS[confirmed_context['scenario']]}")
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def on_progress(idx, total, label):
                progress_bar.progress(idx / total * 0.7)
                status_text.write(f"{idx}/{total} — {label} 생성 중...")

            try:
                from core.report_generator import run_all_calls
                results = run_all_calls(confirmed_context, progress_callback=on_progress)
                st.session_state.chapter_results = results

                status_text.write("차트 6종 생성 중...")
                progress_bar.progress(0.8)
                from core.chart_generator import generate_all_charts
                chart_images = generate_all_charts(results)

                status_text.write("Word 문서 조립 중...")
                progress_bar.progress(0.95)
                from core.docx_builder import build_report_docx
                import datetime
                docx_buf = build_report_docx(
                    tech_name=confirmed_context["tech_name"],
                    purpose=confirmed_context["purpose"] or config.DEFAULT_PURPOSE,
                    scenario_label=config.SCENARIO_LABELS[confirmed_context["scenario"]],
                    date_str=datetime.date.today().strftime("%Y년 %m월"),
                    chapter_results=results,
                    chart_images=chart_images,
                    confirmed_context=confirmed_context,
                )
                progress_bar.progress(1.0)
                status_text.write("문서 생성 완료")
                st.session_state.docx_buffer = docx_buf
                fname = f"{confirmed_context['tech_name'].replace(' ', '_')}_기술동향분석.docx"
                st.download_button(
                    "📥 Word 문서 다운로드",
                    data=st.session_state.docx_buffer,
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    width='stretch',
                )
            except Exception as e:
                st.session_state.gen_error = str(e)
                st.error(f"보고서 생성 중 오류가 발생했습니다:\n\n{st.session_state.gen_error}")

# =================================================================
# 생성 화면: 챕터 생성 → 차트 → 문서 조립 → 다운로드
# =================================================================
elif st.session_state.step == "generate":
    st.subheader("보고서 생성")

    confirmed_context = dict(
        tech_name=st.session_state.inputs["tech_name"],
        scenario=st.session_state.call1_result["scenario"],
        org_name=st.session_state.inputs["org_name"],
        org_capability=st.session_state.inputs["org_capability"],
        attachment_summary=st.session_state.inputs.get("attachment_summary"),
        classification=st.session_state.confirmed_classification,
        purpose=st.session_state.inputs["purpose"],
    )
    confirmed_context["research_plan"] = build_research_plan(
        confirmed_context["tech_name"],
        confirmed_context["classification"],
        confirmed_context.get("attachment_summary"),
    )

    if "chapter_results" not in st.session_state:
        st.session_state.chapter_results = None
    if "docx_buffer" not in st.session_state:
        st.session_state.docx_buffer = None
    if "gen_error" not in st.session_state:
        st.session_state.gen_error = None

    if st.session_state.docx_buffer is None:
        st.info(f"자동 적용 시나리오: {config.SCENARIO_LABELS[confirmed_context['scenario']]}")
        with st.expander("자동 분류 및 무료 공개자료 기반 조사 계획", expanded=False):
            st.markdown(f"**기술 분야 유형**: {st.session_state.call1_result.get('field_type')}")
            st.dataframe(confirmed_context["classification"], width='stretch')
            plan = confirmed_context["research_plan"]
            st.write(plan["input_basis"])
            st.markdown("**특허 검증 링크**")
            st.dataframe(plan["patent_search_links"], width='stretch')
            st.markdown("**논문/시장 검증 링크**")
            st.dataframe(plan["scholar_search_links"] + plan["market_search_links"], width='stretch')

        should_generate = st.button("보고서 다시 생성", type="primary", width='stretch')

        if should_generate:
            st.session_state.gen_error = None
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def on_progress(idx, total, label):
                progress_bar.progress(idx / total * 0.7)
                status_text.write(f"{idx}/{total} — {label} 생성 중...")

            try:
                from core.report_generator import run_all_calls
                results = run_all_calls(confirmed_context, progress_callback=on_progress)
                st.session_state.chapter_results = results

                status_text.write("차트 6종 생성 중...")
                progress_bar.progress(0.8)
                from core.chart_generator import generate_all_charts
                chart_images = generate_all_charts(results)

                status_text.write("Word 문서 조립 중...")
                progress_bar.progress(0.95)
                from core.docx_builder import build_report_docx
                import datetime
                docx_buf = build_report_docx(
                    tech_name=confirmed_context["tech_name"],
                    purpose=confirmed_context["purpose"] or config.DEFAULT_PURPOSE,
                    scenario_label=config.SCENARIO_LABELS[confirmed_context["scenario"]],
                    date_str=datetime.date.today().strftime("%Y년 %m월"),
                    chapter_results=results,
                    chart_images=chart_images,
                    confirmed_context=confirmed_context,
                )
                progress_bar.progress(1.0)
                st.session_state.docx_buffer = docx_buf
                st.rerun()
            except Exception as e:
                st.session_state.gen_error = str(e)
                st.rerun()

        if st.session_state.gen_error:
            st.error(f"보고서 생성 중 오류가 발생했습니다:\n\n{st.session_state.gen_error}")

        if st.session_state.chapter_results:
            with st.expander("🔧 고급: 생성된 원본 데이터 보기 (디버깅용)", expanded=False):
                any_mock = any(v.get("mock") for v in st.session_state.chapter_results.values())
                if any_mock:
                    st.info("MOCK 응답 포함 — 실제 API 연결 전 구조 검증용입니다.", icon="🧪")
                for call_id, label in [("call2", "Ⅰ·Ⅱ장"), ("call3", "Ⅲ·Ⅳ장"), ("call4", "Ⅴ장"),
                                        ("call5", "Ⅵ·Ⅶ장"), ("call6", "Ⅷ·Ⅸ장")]:
                    if call_id in st.session_state.chapter_results:
                        st.markdown(f"**{label}**")
                        st.json(st.session_state.chapter_results[call_id])
    else:
        st.success("문서 생성 완료")
        fname = f"{confirmed_context['tech_name'].replace(' ', '_')}_기술동향분석.docx"
        st.download_button(
            "📥 Word 문서 다운로드",
            data=st.session_state.docx_buffer,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            width='stretch',
        )
        with st.expander("🔧 고급: 생성된 원본 데이터 보기 (디버깅용)", expanded=False):
            for call_id, label in [("call2", "Ⅰ·Ⅱ장"), ("call3", "Ⅲ·Ⅳ장"), ("call4", "Ⅴ장"),
                                    ("call5", "Ⅵ·Ⅶ장"), ("call6", "Ⅷ·Ⅸ장")]:
                st.markdown(f"**{label}**")
                st.json(st.session_state.chapter_results[call_id])

    if st.button("← 처음부터 다시"):
        for k in ["step", "call1_result", "confirmed_classification", "chapter_results",
                  "docx_buffer", "gen_error"]:
            st.session_state.pop(k, None)
        st.rerun()
