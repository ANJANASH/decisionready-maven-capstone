"""Presentation-quality Streamlit UI for the frozen DecisionReady capstone."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from decisionready_demo import MAX_TOOL_CALLS, STATUS_TARGETS, assess_text, benchmark_proposals


st.set_page_config(
    page_title="DecisionReady — Enterprise Decision Pre-Flight",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #162338;
        --navy: #183654;
        --blue: #315d83;
        --muted: #667386;
        --line: #dfe5eb;
        --soft: #f6f8fa;
        --ready: #346b53;
        --ready-bg: #f3f8f5;
        --caveat: #9a6720;
        --caveat-bg: #fcf8ef;
        --critical: #9a4141;
        --critical-bg: #fbf4f4;
    }
    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .stApp { background: #ffffff; color: var(--ink); }
    .block-container { max-width: 1180px; padding-top: 3.25rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background: #f7f9fb; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] .block-container { padding-top: 1.7rem; }
    h1, h2, h3 { color: var(--navy); letter-spacing: -0.015em; }
    h2 { font-size: 1.28rem !important; margin-top: 1.7rem !important; }
    h3 { font-size: 1.02rem !important; margin-top: 1.2rem !important; }
    .product-header { border-bottom: 1px solid var(--line); padding: 0.55rem 0 1.05rem 0; margin-bottom: 1.3rem; overflow: visible; }
    .wordmark { color: var(--navy); font-size: 2.05rem; font-weight: 730; letter-spacing: -0.045em; line-height: 1.25; padding-top: 0.08rem; overflow: visible; }
    .product-subtitle { color: var(--ink); font-size: 1.02rem; font-weight: 560; margin-top: 0.42rem; }
    .product-principles { color: var(--muted); font-size: 0.86rem; margin-top: 0.2rem; }
    .eyebrow { color: var(--blue); font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; }
    .decision-text { color: var(--ink); font-size: 1.08rem; line-height: 1.55; max-width: 900px; margin: 0.3rem 0 0.85rem 0; }
    .status-panel { border: 1px solid var(--line); border-left-width: 5px; padding: 0.9rem 1.05rem; margin: 0.45rem 0 0.85rem 0; }
    .status-ready { border-left-color: var(--ready); background: var(--ready-bg); }
    .status-caveats { border-left-color: var(--caveat); background: var(--caveat-bg); }
    .status-not-ready { border-left-color: var(--critical); background: var(--critical-bg); }
    .status-neutral { border-left-color: #6d7887; background: var(--soft); }
    .status-kicker { color: var(--muted); font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
    .status-value { color: var(--ink); font-size: 1.52rem; font-weight: 730; margin-top: 0.08rem; }
    .why-panel { border-left: 3px solid #a8b8c8; padding: 0.15rem 0 0.15rem 0.9rem; margin: 0.8rem 0 1.1rem 0; }
    .why-title { color: var(--navy); font-size: 0.84rem; font-weight: 700; margin-bottom: 0.18rem; }
    .why-copy { color: #354256; font-size: 0.94rem; line-height: 1.5; }
    .section-rule { border-top: 1px solid var(--line); margin-top: 1.5rem; padding-top: 0.05rem; }
    .section-intro { color: var(--muted); font-size: 0.86rem; margin-top: -0.25rem; margin-bottom: 0.65rem; }
    .compact-item { border-bottom: 1px solid #ebeff3; padding: 0.55rem 0 0.65rem 0; }
    .compact-item:last-child { border-bottom: 0; }
    .item-title { color: var(--ink); font-weight: 650; font-size: 0.94rem; }
    .item-copy { color: #4c596c; font-size: 0.88rem; line-height: 1.45; margin-top: 0.16rem; }
    .priority-row { display: grid; grid-template-columns: 1.55rem 1fr; gap: 0.35rem; margin: 0.5rem 0; }
    .priority-number { color: var(--blue); font-weight: 720; }
    .priority-copy { color: #364358; font-size: 0.91rem; line-height: 1.45; }
    .tool-summary { border: 1px solid var(--line); background: var(--soft); padding: 0.9rem 1rem; margin-top: 0.6rem; }
    .tool-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.8rem; }
    .tool-label { color: var(--muted); font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
    .tool-value { color: var(--ink); font-size: 0.93rem; font-weight: 650; margin-top: 0.14rem; }
    .tool-why { color: #455267; font-size: 0.88rem; line-height: 1.45; margin-top: 0.7rem; }
    .workbook-line { color: #455267; font-size: 0.86rem; margin-top: 0.55rem; }
    .sidebar-note { border-top: 1px solid var(--line); margin-top: 1rem; padding-top: 0.85rem; color: var(--muted); font-size: 0.82rem; line-height: 1.45; }
    [data-testid="stMetric"] { border: 1px solid var(--line); padding: 0.72rem 0.8rem; background: #ffffff; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); font-size: 1.15rem; }
    [data-testid="stExpander"] { border-color: var(--line); border-radius: 2px; background: #ffffff; }
    div.stButton > button { background: var(--navy); color: #ffffff; border: 1px solid var(--navy); border-radius: 4px; font-weight: 650; min-height: 2.75rem; }
    div.stButton > button:hover { background: #244d70; color: #ffffff; border-color: #244d70; }
    @media (max-width: 760px) {
        .tool-grid { grid-template-columns: 1fr; }
        .wordmark { font-size: 1.75rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "question", "action", "claim", "description", "rationale"):
            if value.get(key):
                return str(value[key])
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _item_title(item: dict[str, Any]) -> str:
    return str(
        item.get("related_item_text")
        or item.get("blocker_code")
        or item.get("caveat_code")
        or "Structured item"
    )


def _human_tool(tool: str) -> str:
    return "None" if tool == "none" else tool.replace("_", " ").title()


def _status_style(status: str) -> tuple[str, str]:
    return {
        "READY": ("status-ready", "READY"),
        "READY_WITH_CAVEATS": ("status-caveats", "READY WITH CAVEATS"),
        "NOT_READY": ("status-not-ready", "NOT READY"),
    }.get(status, ("status-neutral", status.replace("_", " ")))


def _why_status(result: dict[str, Any]) -> str:
    status = result["readiness_status"]
    blockers = result.get("hard_blockers", [])
    caveats = result.get("material_caveats", [])
    trace = result["tool_trace"]
    if status == "READY":
        return (
            "The requested decision is sufficiently bounded for leadership review. No hard blocker or current-decision "
            "material caveat is present, and additional evidence acquisition would not improve this pilot decision."
        )
    if status == "NOT_READY":
        first = blockers[0].get("rationale", "A decision-stopping issue remains unresolved.") if blockers else "A decision-stopping issue remains unresolved."
        return first
    if status == "READY_WITH_CAVEATS":
        if result.get("benchmark") == "Proposal E":
            return (
                "The pilot can proceed as a bounded test, but the financial model contains seven material limitations. "
                "Arithmetic reconciles; economic horizons, assumptions, sensitivities, and benefit attribution need leadership attention."
            )
        return (
            f"No hard blocker is confirmed, but {len(caveats)} material uncertainty remains relevant to the current pilot. "
            f"The evidence effect is {trace.get('evidence_effect', 'mixed')}; unresolved items stay visible without stopping the decision."
        )
    return "Frozen mode captured the input but did not run a canonical assessment."


def _render_status(result: dict[str, Any]) -> None:
    css, label = _status_style(result["readiness_status"])
    st.markdown(
        f'<div class="status-panel {css}"><div class="status-kicker">Readiness</div>'
        f'<div class="status-value">{label}</div></div>',
        unsafe_allow_html=True,
    )


def _render_reasoning(items: list[dict[str, Any]], empty: str, limit: int | None = None) -> None:
    shown = items if limit is None else items[:limit]
    if not shown:
        st.caption(empty)
        return
    for item in shown:
        st.markdown(
            f'<div class="compact-item"><div class="item-title">{_item_title(item)}</div>'
            f'<div class="item-copy">{item.get("rationale", "")}</div></div>',
            unsafe_allow_html=True,
        )


def _render_numbered(items: list[Any], empty: str, limit: int = 3) -> None:
    if not items:
        st.caption(empty)
        return
    for index, item in enumerate(items[:limit], start=1):
        copy = item.get("gap", "") if isinstance(item, dict) and "gap" in item else _clean(item)
        st.markdown(
            f'<div class="priority-row"><div class="priority-number">{index}</div>'
            f'<div class="priority-copy">{copy}</div></div>',
            unsafe_allow_html=True,
        )


def _render_tool_summary(result: dict[str, Any]) -> None:
    trace = result["tool_trace"]
    tool = _human_tool(trace.get("selected_tool", "none"))
    effect = trace.get("evidence_effect", "Not applicable").replace("_", " ").title()
    st.markdown(
        '<div class="tool-summary">'
        '<div class="tool-grid">'
        f'<div><div class="tool-label">Tool used</div><div class="tool-value">{tool}</div></div>'
        f'<div><div class="tool-label">Calls used</div><div class="tool-value">{trace.get("calls_used", 0)} of {MAX_TOOL_CALLS}</div></div>'
        f'<div><div class="tool-label">Evidence effect</div><div class="tool-value">{effect}</div></div>'
        '</div>'
        f'<div class="tool-why"><strong>Why:</strong> {trace.get("why", "No rationale recorded.")}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    workbook = result.get("workbook_analysis")
    if workbook:
        st.markdown(
            f'<div class="workbook-line"><strong>Workbook detected</strong> · '
            f'{len(workbook["sheet_names"])} sheets · {workbook["formula_count"]} formula cells inspected · local-only analysis</div>',
            unsafe_allow_html=True,
        )


def _render_e_findings(result: dict[str, Any]) -> None:
    findings = result.get("material_caveats", [])
    with st.expander("View all spreadsheet findings", expanded=False):
        for index, finding in enumerate(findings, start=1):
            st.markdown(f"**{index}. {_item_title(finding)}**")
            st.caption(
                f"Finding type: {finding.get('caveat_code', 'other').lower()} · "
                "Severity: material caveat"
            )
            st.write(finding.get("rationale", ""))
            refs = finding.get("evidence", [])
            if refs:
                st.code(" · ".join(refs), language=None)


def _render_audit_expanders(result: dict[str, Any]) -> None:
    with st.expander("Evidence & assumptions", expanded=False):
        items = result.get("evidence_assumptions", [])
        if items:
            for item in items:
                st.markdown(f"- {_clean(item)}")
        else:
            st.caption("No material evidence or assumptions recorded.")

    with st.expander("View all identified gaps", expanded=False):
        gaps = result.get("missing_information", [])
        if gaps:
            st.dataframe(gaps, width="stretch", hide_index=True)
        else:
            st.caption("No material missing information identified.")

    with st.expander("Dependencies & risks", expanded=False):
        left, right = st.columns(2)
        with left:
            st.markdown("**Dependencies**")
            for item in result.get("dependencies", []):
                st.markdown(f"- {_clean(item)}")
            if not result.get("dependencies"):
                st.caption("None recorded.")
        with right:
            st.markdown("**Risks**")
            for item in result.get("risks", []):
                st.markdown(f"- {_clean(item)}")
            if not result.get("risks"):
                st.caption("None recorded.")

    with st.expander("Future-decision considerations", expanded=False):
        future = result.get("future_considerations", [])
        if future:
            for item in future:
                st.markdown(f"**{item.get('related_item_text', 'Future decision')}**")
                st.write(item.get("rationale", ""))
        else:
            st.caption("No separate future-decision consideration recorded.")

    trace = result["tool_trace"]
    with st.expander("Detailed evidence trace", expanded=False):
        if trace.get("evidence_summary"):
            st.markdown("**Evidence interpretation**")
            for item in trace["evidence_summary"]:
                st.markdown(f"- {item}")
        st.markdown("**Remaining uncertainty**")
        remaining = trace.get("unresolved_evidence", [])
        if remaining:
            for item in remaining:
                st.markdown(f"- {item}")
        else:
            st.caption("No unresolved evidence recorded.")
        if result.get("grounded_requirements"):
            st.markdown("**Grounded requirements**")
            for item in result["grounded_requirements"]:
                status = item.get("requirement_status", "unclear").replace("_", " ")
                st.markdown(f"- {item.get('requirement_text', 'Requirement')} — **{status}**")
                if item.get("supporting_source_ids"):
                    st.caption("Sources: " + ", ".join(item["supporting_source_ids"]))

    with st.expander("Advanced trace", expanded=False):
        st.json(trace, expanded=False)

    if result.get("workbook_analysis"):
        workbook = result["workbook_analysis"]
        with st.expander("Workbook inspection detail", expanded=False):
            st.write("Sheets inspected: " + ", ".join(workbook["sheet_names"]))
            st.dataframe(workbook["formula_checks"], width="stretch", hide_index=True)
            st.caption(f"Local SHA-256: {workbook['sha256']}")

    with st.expander("Full audit brief", expanded=False):
        st.write(result.get("final_brief", "No final brief was persisted."))


def _render_result(result: dict[str, Any]) -> None:
    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.markdown("## Executive Decision Readiness Brief")
    st.markdown('<div class="eyebrow">Decision requested</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="decision-text">{result["decision_requested"]}</div>', unsafe_allow_html=True)
    _render_status(result)

    blockers = result.get("hard_blockers", [])
    caveats = result.get("material_caveats", [])
    trace = result["tool_trace"]
    k1, k2, k3 = st.columns(3)
    k1.metric("Hard blockers", len(blockers))
    k2.metric("Material caveats", len(caveats))
    k3.metric("Tool used", _human_tool(trace.get("selected_tool", "none")))

    st.markdown(
        f'<div class="why-panel"><div class="why-title">Why this status</div>'
        f'<div class="why-copy">{_why_status(result)}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Hard blockers")
    _render_reasoning(blockers, "No hard blockers identified.")

    st.markdown("### Material caveats")
    caveat_limit = 4 if result.get("benchmark") == "Proposal E" else None
    _render_reasoning(caveats, "No current-decision material caveats identified.", limit=caveat_limit)
    if caveat_limit and len(caveats) > caveat_limit:
        st.caption(f"Showing the four most decision-relevant caveats. {len(caveats) - caveat_limit} additional findings remain in the audit detail.")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Priority gaps")
        _render_numbered(result.get("missing_information", []), "No material priority gaps identified.")
        st.markdown("### Leadership challenge questions")
        _render_numbered(result.get("leadership_questions", []), "No additional leadership questions recorded.")
    with right:
        st.markdown("### Recommended pre-review actions")
        _render_numbered(result.get("recommended_actions", []), "No additional pre-review actions recorded.")
        st.markdown("### Evidence / tool summary")
        _render_tool_summary(result)

    if result.get("benchmark") == "Proposal E":
        _render_e_findings(result)

    st.markdown("## Audit detail")
    st.markdown('<div class="section-intro">Complete structured evidence remains available below for review and traceability.</div>', unsafe_allow_html=True)
    _render_audit_expanders(result)


st.markdown(
    """
    <div class="product-header">
      <div class="wordmark">DecisionReady</div>
      <div class="product-subtitle">Enterprise Decision Pre-Flight</div>
      <div class="product-principles">Evidence-first assessment · Bounded autonomy · Decision support, not decision-making</div>
    </div>
    """,
    unsafe_allow_html=True,
)

proposals = benchmark_proposals()

with st.sidebar:
    st.markdown("## Demo mode")
    st.caption("Uses validated frozen evidence for deterministic presentation.")
    benchmark = st.selectbox(
        "Benchmark proposal",
        ["Custom proposal", *STATUS_TARGETS.keys()],
        index=1,
        help="A–E reproduce the persisted v0.7 benchmark traces.",
    )
    uploaded_workbook = st.file_uploader(
        "Supporting Excel file",
        type=["xlsx"],
        help="Proposal E uses the authoritative local workbook when no file is uploaded.",
    )
    st.markdown(
        '<div class="sidebar-note"><strong>Frozen presentation mode</strong><br>'
        'Live arbitrary proposals are intentionally not assessed. Workbook inspection remains local. '
        f'Maximum tool calls: {MAX_TOOL_CALLS}.</div>',
        unsafe_allow_html=True,
    )

previous_benchmark = st.session_state.get("last_benchmark")
if previous_benchmark != benchmark:
    st.session_state["proposal_input"] = proposals.get(benchmark, "")
    st.session_state["last_benchmark"] = benchmark
    st.session_state.pop("assessment_result", None)

st.markdown("## Proposal")
st.markdown('<div class="section-intro">Review the decision request, then run the frozen pre-flight assessment.</div>', unsafe_allow_html=True)
proposal_text = st.text_area(
    "Proposal text",
    key="proposal_input",
    height=285,
    placeholder="Paste the decision proposal here…",
)
if benchmark == "Custom proposal":
    st.caption("Custom text stays local and is not assigned a readiness status in frozen mode.")
assess_clicked = st.button("Assess Decision Readiness", type="primary", width="stretch")

if assess_clicked:
    try:
        if uploaded_workbook is not None:
            with tempfile.TemporaryDirectory(prefix="decisionready_demo_") as temp_dir:
                workbook_path = Path(temp_dir) / uploaded_workbook.name
                workbook_path.write_bytes(uploaded_workbook.getvalue())
                st.session_state["assessment_result"] = assess_text(
                    proposal_text,
                    selected_benchmark=benchmark,
                    workbook_path=workbook_path,
                )
        else:
            st.session_state["assessment_result"] = assess_text(
                proposal_text,
                selected_benchmark=benchmark,
            )
    except Exception as exc:
        st.session_state.pop("assessment_result", None)
        st.error(f"The local assessment could not be completed: {exc}")

result = st.session_state.get("assessment_result")
if result:
    _render_result(result)
else:
    st.info("Select a benchmark or paste proposal text, then assess decision readiness.")


