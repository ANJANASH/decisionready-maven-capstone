# DecisionReady Maven Demo

This lightweight Streamlit app demonstrates the frozen DecisionReady Iteration 3 v0.7 experience. It reproduces the persisted Proposal A–E benchmark traces without relying on OpenAI, Tavily, or another live service during a presentation.

## Start the app

From the project folder:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements_demo.txt
C:\Users\anjan\problem_first_ai\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit normally opens `http://localhost:8501`.

## Demo flow

1. Select Proposal A–E in **Demo controls**.
2. Review or edit the proposal text.
3. Optionally upload an `.xlsx` file.
4. Select **Assess Decision Readiness**.
5. Review the readiness brief and the compact evidence/tool trace.

The frozen benchmark results are:

| Proposal | Readiness | Tool outcome |
|---|---|---|
| A | READY | none |
| B | NOT_READY | none |
| C | NOT_READY | none; authoritative evidence already exists |
| D | READY_WITH_CAVEATS | external_search, replayed frozen evidence |
| E | READY_WITH_CAVEATS | spreadsheet_analysis, local workbook inspection |

The separate synthetic policy fixture retained by v0.7 demonstrates that `internal_retrieval` remains reachable when a genuinely unresolved internal-policy question exists.

## Proposal E

When Proposal E is selected and no file is uploaded, the app reads the authoritative workbook at:

`inputs/proposal_e/DecisionReady_Proposal_E_Financial_Model.xlsx`

Inspection stays local. The app displays sheet names, formula count, headline formula cells, and the seven validated quantitative caveats. An uploaded workbook is compared by SHA-256 with the authoritative artifact. If it differs, the app shows structural metadata but does not attribute the frozen Proposal E findings to that uploaded file.

## Frozen-mode boundaries

- `MAX_TOOL_CALLS` remains 2.
- Tool evidence never directly sets readiness or creates a blocker.
- `none` remains a valid outcome.
- No live external search, model call, autonomous loop, or new retrieval infrastructure is included.
- The app reads persisted notebook fixtures; it does not execute or dynamically import notebook cells.
- Editing benchmark text turns it into a custom input. In frozen mode, arbitrary custom text is captured but marked `NOT_ASSESSED` rather than sent externally or assessed with invented substitute logic.

This is a presentation interface, not a production service. It has no authentication, persistence, deployment configuration, or live custom-proposal assessment.

