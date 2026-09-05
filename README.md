# DecisionReady — Enterprise Decision Pre-Flight Agent
DecisionReady is a Maven GenAI System Design capstone that assesses whether an enterprise proposal is decision-ready for leadership review — not whether leadership should approve it.

# What it does
DecisionReady reviews a proposal and surfaces:
- Decision requested
- Readiness: READY / READY_WITH_CAVEATS / NOT_READY
- Hard blockers
- Material caveats
- Evidence and assumptions
- Missing information
- Dependencies and risks
- Leadership challenge questions
- Recommended pre-review actions

# Iteration journey
- Iteration 1: Proposal-only reasoning
- Iteration 2: Grounded internal evidence / policy retrieval
- Iteration 3: Bounded autonomy with selective tool use

Final supported tool outcomes:
- none
- internal_retrieval
- external_search
- spreadsheet_analysis
Core design principle:
  # Tools acquire evidence; they do not directly decide readiness.

# Demo benchmark
Case	Tool	Outcome
A	    none	READY
B	    none	NOT_READY
C	    none	NOT_READY
D	  external search	READY_WITH_CAVEATS
E	  spreadsheet analysis	READY_WITH_CAVEATS
Synthetic policy case	internal retrieval	branch validation


# Demo
The Streamlit app runs in deterministic demo mode using validated frozen evidence for reproducible presentation.
See:
- README_Demo.md
- app.py
- DecisionReady_Iteration3_v07.ipynb
- DecisionReady_Iteration3_v07_Audit_Snapshot.md

# Notes
The demo intentionally does not assess arbitrary pasted proposals live. This keeps the Maven presentation reproducible and prevents unsupported outputs.
