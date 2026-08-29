# Demo guide

## Recommended story

Use `SCN004` as the primary walkthrough because it demonstrates normal evidence gathering, a recoverable tool failure, a bounded retry, alternate authorization lookup, and an evidence-backed resolution. If time allows, briefly show `SCN003` to demonstrate that orchestration also avoids unnecessary systems.

The polished console runs in validated playback mode. It does not depend on local n8n or an external model during the presentation.

## Before recording

1. From the repository root, start Streamlit:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
   ```

2. Open the local URL printed by Streamlit, normally `http://localhost:8501`.
3. Confirm the header shows **Validated playback**.
4. Select `SCN004 · Payer system failure and recovery`.
5. Keep browser zoom at a comfortable level and close unrelated tabs or terminals that might expose private information.
6. Do not open `.env`, n8n credentials, raw model output, or debug trace content during the recording.

## Suggested 3–5 minute sequence

### 0:00–0:35 · Frame the problem

- Introduce OneCall AI as a healthcare payer resolution copilot.
- Explain that one member issue can span eligibility, benefits, claims, authorization, and provider systems.
- State the key promise: the member explains the problem once, and the system coordinates the rest.

### 0:35–1:15 · Show intake and request flow

- Point to Call/Chat selection and choose **Call**.
- Select `SCN004`.
- Show the scenario-driven member ID, service code, service date, and member inquiry.
- Point to the member inquiry in the intake card and explain that it is captured once in shared case context.
- Follow the adjacent request-flow diagram from intake through orchestrated checks and back to the representative.
- Click **Start resolution**.

### 1:15–2:20 · Follow orchestration and recovery

- Show the five complete stage badges: Intake, Orchestrator, Tool checks, Evidence synthesis, and Recommendation.
- Expand the trace story: the system verifies coverage and benefits, reviews the denied claim, attempts authorization, records the primary failure and retry failure, then uses alternate lookup.
- Point out the recovery banner and the selected case path.
- Emphasize that retry is bounded and evidence remains in shared case state.

### 2:20–2:55 · Explain the architecture

- Follow the embedded diagram from single member intake to the Streamlit console and Main Orchestrator.
- Point out the Orchestrator Agent, five deterministic payer-domain tools, and Resolution Agent.
- Explain that deterministic tools own payer facts while agents make constrained planning and synthesis decisions.
- Close the loop at representative approval or human review.

### 2:55–3:40 · Show the final decision

- Show the workflow status, human approval requirement, and **Member transfer required: No**.
- Read the root cause: authorization-claim link failure.
- Read the next action: claim reconsideration.
- Highlight the supporting evidence, especially the failed primary path and successful alternate authorization evidence.
- Click **Approve recommended action** or **Escalate to specialist** and explain that this is a UI decision boundary only; no payer record is changed.

### 3:40–4:15 · Show operational and validation value

- Point to one member explanation and avoided transfer.
- Explain faster evidence collection, reduced manual navigation, and more consistent investigation—not financial estimates.
- Show the factual validation evidence: agentic scenarios `4/4`, domain tool suite `PASS`, synthetic data.

### Optional 4:15–4:45 · Contrast with SCN003

- Select `SCN003` and start resolution.
- Show that only eligibility and enrollment/benefits evidence is needed.
- Explain that Claims, Authorization, and Provider checks are avoided because they cannot help resolve this mismatch.

## What to emphasize

- Single member intake and one retained explanation.
- Shared case state across the entire investigation.
- Deterministic payer facts and bounded agent decisions.
- Visible recovery rather than an invisible retry loop.
- Evidence-backed representative action with a human boundary.
- No repeated transfers or repeated storytelling.

## What not to claim

- Do not claim dollar savings, ROI, production readiness, real-member use, or autonomous payer updates.
- Do not describe controlled playback as a live n8n call.
- Do not claim a newly refreshed model evaluation unless it was actually run and observed.
- Do not expose secrets, raw model content, or local environment values.

## Fast fallback

If a browser refresh resets the session, reselect `SCN004` and click **Start resolution**. Because the playback uses local validated fixtures, it does not require network access and should return immediately.
