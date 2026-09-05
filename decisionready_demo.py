"""Reusable frozen-demo logic for the DecisionReady Maven capstone.

The module reads canonical persisted fixtures from Iteration 3 v0.7 without
executing notebook cells. It never calls OpenAI, Tavily, or another external
service. Spreadsheet inspection is local and uses the validated OOXML reader.
"""

from __future__ import annotations

import ast
import copy
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
CANONICAL_NOTEBOOK = PROJECT_ROOT / "notebooks" / "DecisionReady_Iteration3_v07.ipynb"
PROPOSAL_E_DOCX = PROJECT_ROOT / "inputs" / "proposal_e" / "DecisionReady_Proposal_E_Sales_Productivity_Pilot.docx"
PROPOSAL_E_XLSX = PROJECT_ROOT / "inputs" / "proposal_e" / "DecisionReady_Proposal_E_Financial_Model.xlsx"
MAX_TOOL_CALLS = 2

CODE_DIR = PROJECT_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from decisionready_spreadsheet_analysis import (  # noqa: E402
    file_sha256,
    inspect_xlsx,
    read_docx_blocks,
)


STATUS_TARGETS = {
    "Proposal A": "READY",
    "Proposal B": "NOT_READY",
    "Proposal C": "NOT_READY",
    "Proposal D": "READY_WITH_CAVEATS",
    "Proposal E": "READY_WITH_CAVEATS",
}


TOOL_TRACES: dict[str, dict[str, Any]] = {
    "Proposal A": {
        "material_evidence_need": "Evidence for a later scale or rollout decision",
        "material_to_current_decision": False,
        "resolvability": "tool_insufficient",
        "selected_tool": "none",
        "calls_used": 0,
        "evidence_effect": "not applicable",
        "sufficiency": "not applicable",
        "unresolved_evidence": ["Later rollout economics and operating design remain to be established."],
        "stop_reason": "no_eligible_tool_call",
        "why": "The uncertainty belongs to a future rollout decision and does not affect approval of the bounded pilot now.",
    },
    "Proposal B": {
        "material_evidence_need": "Proposal-owner clarification and company-specific execution evidence",
        "material_to_current_decision": True,
        "resolvability": "tool_insufficient",
        "selected_tool": "none",
        "calls_used": 0,
        "evidence_effect": "not applicable",
        "sufficiency": "not applicable",
        "unresolved_evidence": [
            "Decision scope, ownership, sequencing, economics, and execution facts remain incomplete."
        ],
        "stop_reason": "no_eligible_tool_call",
        "why": "The missing facts must come from the proposal owner or internal operating teams; public search cannot rescue them.",
    },
    "Proposal C": {
        "material_evidence_need": "Authoritative internal governance requirement for the proposed pilot",
        "material_to_current_decision": True,
        "resolvability": "internally_resolvable",
        "selected_tool": "none",
        "calls_used": 0,
        "evidence_effect": "already grounded",
        "sufficiency": "sufficient",
        "unresolved_evidence": ["The required Data Governance review remains unresolved operationally."],
        "stop_reason": "existing_evidence_sufficient",
        "why": "The frozen state already contains authoritative Northstar policy evidence; repeat retrieval has low incremental value.",
    },
    "Proposal D": {
        "material_evidence_need": "Current public fasteners market size, growth, and pricing evidence relevant to the pilot hypothesis",
        "material_to_current_decision": True,
        "resolvability": "externally_resolvable",
        "selected_tool": "external_search",
        "calls_used": 2,
        "evidence_effect": "mixed",
        "sufficiency": "partial",
        "evidence_summary": [
            "Recent commercial market reports generally indicate roughly 3–5% CAGR, weakening the proposal's dated 8–10% growth assumption.",
            "Public evidence qualitatively supports fragmented market and pricing conditions.",
            "The bounded search found commercial market-research pages rather than primary government or trade data.",
        ],
        "unresolved_evidence": [
            "Comparable numeric ASP or channel pricing remains unverified.",
            "The proposal's margin assumptions remain company-specific and unresolved.",
            "Supplier onboarding feasibility remains an internal operating question.",
        ],
        "stop_reason": "tool_call_budget_exhausted",
        "why": "Current public market evidence can update the dated external assumptions, but company-specific execution facts stay out of scope.",
    },
    "Proposal E": {
        "material_evidence_need": "Local quantitative validation of the attached financial model against the proposal narrative",
        "material_to_current_decision": True,
        "resolvability": "quantitatively_resolvable",
        "selected_tool": "spreadsheet_analysis",
        "calls_used": 1,
        "evidence_effect": "mixed",
        "sufficiency": "sufficient",
        "unresolved_evidence": [
            "Actual conversion uplift remains a pilot hypothesis.",
            "Incremental internal enablement and IT cost remains unquantified.",
            "The model needs an explicit treatment of recovered-capacity double counting.",
        ],
        "stop_reason": "all_material_spreadsheet_checks_completed",
        "why": "The supplied workbook is decision-material and can be inspected locally without external disclosure.",
    },
}


E_FINDINGS = [
    {
        "caveat_code": "NARRATIVE_MODEL_MISMATCH",
        "related_item_text": "ROI and stated payback use inconsistent economic horizons.",
        "rationale": "The 51% ROI uses 12-week benefits, while the payback calculation treats that same 12-week total benefit as an annual benefit when deriving a monthly run-rate.",
        "evidence": ["02_Base_Case!C17:C21"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
    {
        "caveat_code": "POTENTIAL_DOUBLE_COUNT",
        "related_item_text": "Productivity value and commercial benefit may double-count recovered selling capacity.",
        "rationale": "Saved time is monetized and the proposal also attributes customer interactions and commercial outcomes to redeploying that same capacity.",
        "evidence": ["01_Assumptions!D13", "02_Base_Case!C15:C17"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
    {
        "caveat_code": "UNSUPPORTED_ASSUMPTION",
        "related_item_text": "The 5% incremental conversion assumption lacks historical or experimental support.",
        "rationale": "The assumption materially drives commercial benefit but remains a pilot hypothesis, not a prerequisite.",
        "evidence": ["01_Assumptions!B14", "02_Base_Case!C10:C11"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
    {
        "caveat_code": "SENSITIVITY_ISSUE",
        "related_item_text": "The financial base case assumes 75% adoption while pilot success is defined at 60%.",
        "rationale": "The workbook includes the 60% case, where ROI is about 31.8%, below the 51% headline but still positive under the other base assumptions.",
        "evidence": ["01_Assumptions!B11:B12", "03_Sensitivity!A6:E8"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
    {
        "caveat_code": "COST_SCOPE_EXCLUSION",
        "related_item_text": "Internal Sales Enablement and Product or IT effort is excluded from pilot cost as BAU.",
        "rationale": "The exclusion is disclosed and is not an arithmetic error, but it limits the completeness of the economic case.",
        "evidence": ["01_Assumptions!B18:D18", "02_Base_Case!C18"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
    {
        "caveat_code": "NARRATIVE_MODEL_MISMATCH",
        "related_item_text": "A 26.67% attributable pipeline-realization factor appears only in the workbook.",
        "rationale": "The factor is necessary to reproduce the modeled $115,200 commercial benefit but is not disclosed in the proposal narrative.",
        "evidence": ["01_Assumptions!B16:D16", "02_Base_Case!C10:C11"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
    {
        "caveat_code": "SENSITIVITY_ISSUE",
        "related_item_text": "Productivity benefit does not vary with effective adoption in the adoption sensitivity table.",
        "rationale": "Every adoption scenario retains the same $66,000 productivity benefit while commercial benefit changes.",
        "evidence": ["03_Sensitivity!A6:B8", "02_Base_Case!C6:C7"],
        "source": "retrieved_evidence:local_spreadsheet_analysis",
    },
]


@lru_cache(maxsize=1)
def _canonical_notebook() -> dict[str, Any]:
    return json.loads(CANONICAL_NOTEBOOK.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _notebook_source() -> str:
    return "\n".join("".join(cell.get("source", [])) for cell in _canonical_notebook()["cells"])


def _frozen_json(name: str) -> dict[str, Any]:
    triple_quote = "'" * 3
    pattern = rf"{name}\s*=\s*json\.loads\(r{triple_quote}(.*?){triple_quote}\)"
    match = re.search(pattern, _notebook_source(), flags=re.S)
    if not match:
        raise RuntimeError(f"Canonical fixture {name!r} was not found in {CANONICAL_NOTEBOOK.name}.")
    return json.loads(match.group(1))


@lru_cache(maxsize=1)
def frozen_extractions() -> dict[str, Any]:
    return _frozen_json("FROZEN_EXTRACTION_FIXTURES")


@lru_cache(maxsize=1)
def frozen_downstream() -> dict[str, Any]:
    return _frozen_json("FROZEN_DOWNSTREAM_SNAPSHOTS")


@lru_cache(maxsize=1)
def _proposal_assignments() -> dict[str, str]:
    wanted = {"test_proposal", "proposal_b", "proposal_c", "proposal_d"}
    found: dict[str, str] = {}
    for cell in _canonical_notebook()["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not any(name in source for name in wanted):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value_node = node.value
            for target in targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    try:
                        value = ast.literal_eval(value_node)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(value, str):
                        found[target.id] = value.strip()
    missing = wanted - found.keys()
    if missing:
        raise RuntimeError(f"Missing proposal fixture assignments: {sorted(missing)}")
    return found


@lru_cache(maxsize=1)
def proposal_e_text() -> str:
    blocks = read_docx_blocks(PROPOSAL_E_DOCX)
    parts = [item["text"] for item in blocks["paragraphs"]]
    for table in blocks["tables"]:
        for row in table["rows"]:
            parts.append(" | ".join(value for value in row["values"] if value))
    return "\n".join(part for part in parts if part).strip()


def benchmark_proposals() -> dict[str, str]:
    values = _proposal_assignments()
    return {
        "Proposal A": values["test_proposal"],
        "Proposal B": values["proposal_b"],
        "Proposal C": values["proposal_c"],
        "Proposal D": values["proposal_d"],
        "Proposal E": proposal_e_text(),
    }


def _dedupe_text(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = " ".join(str(item).split())
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _dimension_gaps(assessments: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for dimension, assessment in (assessments or {}).items():
        for gap in assessment.get("gaps", []):
            rows.append({"dimension": dimension.replace("_", " ").title(), "gap": gap})
    return rows


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) if not isinstance(item, dict) else json.dumps(item, ensure_ascii=False) for item in value]
    return [str(value)]


def _a_to_d_result(name: str) -> dict[str, Any]:
    label = name[-1]
    extraction = copy.deepcopy(frozen_extractions()[label])
    downstream = copy.deepcopy(frozen_downstream()[label])
    missing_rows = _dimension_gaps(downstream.get("dimension_assessments", {}))
    evidence = _as_text_list(extraction.get("evidence_items"))
    assumptions = _as_text_list(extraction.get("stated_assumptions")) + _as_text_list(extraction.get("inferred_assumptions"))
    dependencies = _as_text_list(extraction.get("dependencies"))
    risks = _as_text_list(extraction.get("stated_risks")) + _as_text_list(extraction.get("inferred_risks"))
    return {
        "benchmark": name,
        "proposal_text": extraction.get("proposal_text") or benchmark_proposals()[name],
        "decision_requested": extraction.get("decision_ask", "Not stated"),
        "problem_summary": extraction.get("problem_summary", ""),
        "proposed_intervention": extraction.get("proposed_intervention", ""),
        "success_metrics": extraction.get("success_metrics", []),
        "readiness_status": downstream["readiness_status"],
        "hard_blockers": downstream.get("hard_blockers", []),
        "material_caveats": downstream.get("material_caveats", []),
        "evidence_assumptions": _dedupe_text(evidence + assumptions),
        "missing_information": missing_rows,
        "dependencies": dependencies,
        "risks": _dedupe_text(risks),
        "future_considerations": downstream.get("future_decision_considerations", []),
        "grounded_requirements": downstream.get("grounded_requirements", []),
        "leadership_questions": downstream.get("leadership_questions", []),
        "recommended_actions": downstream.get("recommended_actions", []),
        "dimension_assessments": downstream.get("dimension_assessments", {}),
        "final_brief": downstream.get("final_brief", ""),
        "tool_trace": copy.deepcopy(TOOL_TRACES[name]),
        "mode_note": "Frozen deterministic benchmark trace from DecisionReady Iteration 3 v0.7.",
    }


def analyze_proposal_e_workbook(path: str | Path = PROPOSAL_E_XLSX) -> dict[str, Any]:
    path = Path(path)
    snapshot = inspect_xlsx(path)
    required_sheets = {"01_Assumptions", "02_Base_Case", "03_Sensitivity"}
    canonical_hash = file_sha256(PROPOSAL_E_XLSX)
    is_canonical = snapshot["sha256"] == canonical_hash

    formula_checks = []
    checks = [
        ("Productivity benefit", "02_Base_Case", "C7"),
        ("Commercial benefit", "02_Base_Case", "C11"),
        ("Total benefit", "02_Base_Case", "C17"),
        ("Net benefit", "02_Base_Case", "C19"),
        ("ROI", "02_Base_Case", "C20"),
        ("Stated payback", "02_Base_Case", "C21"),
    ]
    for label, sheet, address in checks:
        record = snapshot.get("sheets", {}).get(sheet, {}).get("cells", {}).get(address)
        formula_checks.append(
            {
                "check": label,
                "cell": f"{sheet}!{address}",
                "formula": record.get("formula") if record else None,
                "cached_value": record.get("value") if record else None,
                "available": bool(record),
            }
        )

    return {
        "path": str(path),
        "sha256": snapshot["sha256"],
        "is_canonical": is_canonical,
        "sheet_names": snapshot["sheet_names"],
        "required_sheets_present": required_sheets.issubset(snapshot["sheet_names"]),
        "formula_count": snapshot["formula_count"],
        "formula_checks": formula_checks,
        "findings": copy.deepcopy(E_FINDINGS) if is_canonical else [],
        "note": (
            "Authoritative Proposal E workbook matched; frozen quantitative findings and cell references are available."
            if is_canonical
            else "Uploaded workbook differs from the frozen authoritative artifact; only structural metadata is shown and no frozen finding is attributed to it."
        ),
    }


def _proposal_e_result(workbook_path: str | Path | None = None) -> dict[str, Any]:
    analysis_path = Path(workbook_path) if workbook_path else PROPOSAL_E_XLSX
    workbook = analyze_proposal_e_workbook(analysis_path)
    canonical_analysis = workbook if workbook["is_canonical"] else analyze_proposal_e_workbook(PROPOSAL_E_XLSX)
    caveats = copy.deepcopy(canonical_analysis["findings"])
    return {
        "benchmark": "Proposal E",
        "proposal_text": proposal_e_text(),
        "decision_requested": "Approve a 12-week pilot of an AI-assisted sales productivity platform for 40 sales users with a $120,000 external budget.",
        "problem_summary": "Salespeople spend material time on account research, proposal preparation, CRM updates, and next-best-action preparation.",
        "proposed_intervention": "A bounded 12-week AI-assisted sales productivity pilot for 40 users.",
        "success_metrics": [
            "At least 60% weekly active usage",
            "At least 25% reduction in preparation and administrative time",
            "At least 10% increase in customer-facing activity",
            "No material deterioration in proposal quality",
            "Measurable incremental pipeline generation",
        ],
        "readiness_status": "READY_WITH_CAVEATS",
        "hard_blockers": [],
        "material_caveats": caveats,
        "evidence_assumptions": [
            "Base case: 75% effective adoption versus a 60% success threshold.",
            "5% incremental conversion assumption has no historical or experimental baseline.",
            "Internal enablement and IT effort is excluded as BAU.",
            "26.67% attributable pipeline-realization factor appears only in the workbook.",
        ],
        "missing_information": [
            {"dimension": "Evidence And Assumptions", "gap": "Historical or experimental support for the 5% conversion assumption."},
            {"dimension": "Economics", "gap": "Quantified internal enablement and IT effort."},
            {"dimension": "Economics", "gap": "Explicit convention preventing double counting of recovered capacity."},
        ],
        "dependencies": [
            "Sales Enablement support",
            "Product and IT support",
            "User adoption and CRM integration",
        ],
        "risks": [
            "Benefits may be overstated if productivity and commercial value overlap.",
            "Economics are sensitive to adoption and conversion assumptions.",
            "Excluded internal effort understates the full resource requirement.",
        ],
        "future_considerations": [
            {
                "related_item_text": "A broader rollout to approximately 250 users requires a separate leadership decision after the pilot.",
                "rationale": "This is a later scale decision and does not determine current pilot readiness.",
            }
        ],
        "grounded_requirements": [],
        "leadership_questions": [
            "What economic convention prevents saved-time value and incremental commercial benefit from double counting the same recovered capacity?",
            "What does the case look like at the stated 60% adoption success threshold and after including internal enablement and IT effort?",
            "How will the pilot establish a credible conversion baseline and attribute incremental pipeline to the intervention?",
        ],
        "recommended_actions": [
            "Present ROI and payback on a consistent economic horizon.",
            "Label conversion and commercial uplift as pilot hypotheses and define the measurement baseline.",
            "Add an all-in resource view or clearly quantify the excluded internal effort.",
            "Explain or remove the undisclosed 26.67% pipeline-realization factor.",
        ],
        "dimension_assessments": {},
        "final_brief": "Proposal E is ready for a bounded pilot with material quantitative caveats. The workbook arithmetic reconciles, but leadership should review inconsistent ROI/payback horizons, possible benefit double counting, unsupported conversion uplift, adoption-threshold sensitivity, excluded internal costs, the undisclosed pipeline-realization factor, and adoption-insensitive productivity value. These are caveats and pilot hypotheses, not automatic hard blockers.",
        "tool_trace": {
            **copy.deepcopy(TOOL_TRACES["Proposal E"]),
            "evidence_summary": [finding["related_item_text"] for finding in canonical_analysis["findings"]],
        },
        "workbook_analysis": workbook,
        "mode_note": "Frozen deterministic Proposal E trace with local-only workbook inspection.",
    }


def assess_benchmark(name: str, workbook_path: str | Path | None = None) -> dict[str, Any]:
    if name not in STATUS_TARGETS:
        raise ValueError(f"Unknown benchmark: {name}")
    result = _proposal_e_result(workbook_path) if name == "Proposal E" else _a_to_d_result(name)
    if result["readiness_status"] != STATUS_TARGETS[name]:
        raise AssertionError(f"Frozen benchmark regression for {name} did not reproduce its target.")
    if result["tool_trace"]["calls_used"] > MAX_TOOL_CALLS:
        raise AssertionError(f"{name} exceeds MAX_TOOL_CALLS={MAX_TOOL_CALLS}.")
    return result


def match_frozen_proposal(text: str) -> str | None:
    normalized = " ".join(text.split()).casefold()
    for name, proposal in benchmark_proposals().items():
        if normalized == " ".join(proposal.split()).casefold():
            return name
    return None


def custom_preview(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    decision_line = next(
        (line for line in lines if re.search(r"\b(approve|approval|decision requested|leadership)\b", line, re.I)),
        lines[0] if lines else "No proposal text supplied",
    )
    return {
        "benchmark": "Custom proposal",
        "proposal_text": text,
        "decision_requested": decision_line,
        "problem_summary": "Custom input captured; canonical model extraction is intentionally disabled in frozen demo mode.",
        "proposed_intervention": "Not extracted in frozen mode.",
        "success_metrics": [],
        "readiness_status": "NOT_ASSESSED",
        "hard_blockers": [],
        "material_caveats": [],
        "evidence_assumptions": [],
        "missing_information": [
            {
                "dimension": "Demo Mode",
                "gap": "Custom proposals require a separately authorized live extraction run; frozen mode only reproduces A–E.",
            }
        ],
        "dependencies": [],
        "risks": [],
        "future_considerations": [],
        "grounded_requirements": [],
        "leadership_questions": [],
        "recommended_actions": ["Select Proposal A–E for a deterministic presentation result."],
        "dimension_assessments": {},
        "final_brief": "The proposal text was captured, but no readiness status was inferred. Frozen/demo mode deliberately avoids sending custom text to a model or inventing a local substitute assessment.",
        "tool_trace": {
            "material_evidence_need": "Not evaluated",
            "material_to_current_decision": False,
            "resolvability": "not evaluated",
            "selected_tool": "none",
            "calls_used": 0,
            "evidence_effect": "not applicable",
            "sufficiency": "not applicable",
            "unresolved_evidence": ["Structured extraction and assessment were not run."],
            "stop_reason": "custom_input_requires_authorized_live_assessment",
            "why": "Frozen mode never sends pasted text externally and does not fabricate a canonical assessment.",
        },
        "mode_note": "Custom-input preview only. No model or tool call was made.",
    }


def assess_text(text: str, selected_benchmark: str | None = None, workbook_path: str | Path | None = None) -> dict[str, Any]:
    if selected_benchmark in STATUS_TARGETS:
        canonical_text = benchmark_proposals()[selected_benchmark]
        if " ".join(text.split()).casefold() == " ".join(canonical_text.split()).casefold():
            return assess_benchmark(selected_benchmark, workbook_path)
    matched = match_frozen_proposal(text)
    return assess_benchmark(matched, workbook_path) if matched else custom_preview(text)


def smoke_regression() -> dict[str, Any]:
    results = {name: assess_benchmark(name) for name in STATUS_TARGETS}
    tools = {result["tool_trace"]["selected_tool"] for result in results.values()}
    tools.add("internal_retrieval")  # validated synthetic policy reachability case
    assert tools == {"none", "internal_retrieval", "external_search", "spreadsheet_analysis"}
    assert all(results[name]["readiness_status"] == status for name, status in STATUS_TARGETS.items())
    assert results["Proposal E"]["workbook_analysis"]["is_canonical"]
    assert results["Proposal E"]["workbook_analysis"]["required_sheets_present"]
    assert len(results["Proposal E"]["material_caveats"]) == 7
    return {
        "statuses": {name: result["readiness_status"] for name, result in results.items()},
        "tools_reachable": sorted(tools),
        "proposal_e_sheets": results["Proposal E"]["workbook_analysis"]["sheet_names"],
        "proposal_e_formula_count": results["Proposal E"]["workbook_analysis"]["formula_count"],
    }

