# Demo guide

## Recommended story

Use `SCN001` as the primary walkthrough because it demonstrates cross-domain evidence gathering and the complete human-in-the-loop approval boundary. If time allows, briefly show `SCN004` to demonstrate bounded retry and alternate authorization recovery.

The polished console runs in validated playback mode. It does not depend on local n8n or an external model during the presentation.

## Before recording

1. From the repository root, start Streamlit:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
   ```

2. Open the local URL printed by Streamlit, normally `http://localhost:8501`.
3. Confirm the header shows **Validated playback**.
4. Select `SCN001 · Claim denied despite approved authorization`.
5. Keep browser zoom at a comfortable level and close unrelated tabs or terminals that might expose private information.
6. Do not open `.env`, n8n credentials, raw model output, or debug trace content during the recording.

## Suggested 3–5 minute sequence

### 0:00–0:35 · Frame the problem

- Introduce OneCall AI as a healthcare payer resolution copilot.
- Explain that one member issue can span eligibility, benefits, claims, authorization, and provider systems.
- State the key promise: the member explains the problem once, and the system coordinates the rest.

### 0:35–1:15 · Show intake and request flow

- Point to Call/Chat selection and choose **Call**.
- Select `SCN001`.
- Show the scenario-driven member ID, service code, service date, and member inquiry.
- Point to the member inquiry in the intake card and explain that it is captured once in shared case context.
- Follow the adjacent request-flow diagram from intake through orchestrated checks and back to the representative.
- Click **Start resolution**.

### 1:15–2:20 · Follow orchestration and evidence gathering

- Show the five complete stage badges: Intake, Orchestrator, Tool checks, Evidence synthesis, and Recommendation.
- Expand the trace story: the system verifies coverage and benefits, reviews the denied claim, finds the approved authorization, and validates the provider organization and servicing locations.
- Point out the selected case path and the shared evidence used by the Resolution Agent.
- Emphasize that the member inquiry and evidence remain in one shared case context.

### 2:20–2:55 · Explain the architecture

- Follow the embedded diagram from single member intake to the Streamlit console and Main Orchestrator.
- Point out the Orchestrator Agent, five deterministic payer-domain tools, and Resolution Agent.
- Explain that deterministic tools own payer facts while agents make constrained planning and synthesis decisions.
- Close the loop at representative approval or human review.

### 2:55–3:40 · Show the final decision

- Show the workflow status, human approval requirement, and **Member transfer required: No**.
- Read the root cause: authorization-claim location mismatch.
- Read the next action: claim reconsideration.
- Highlight the denied claim, approved authorization, location mismatch, and in-network provider validation.
- Click **Approve recommended action**.
- Show `READY_FOR_ACTION`, **Member transfer required: No**, **Member must repeat issue: No**, and **Shared case context: Preserved**.
- Explain that a production implementation would submit a governed downstream payer action only after this approval. The prototype stages the recommendation and does not modify a payer record.

### 3:40–4:15 · Show operational and validation value

- Point to one member explanation and avoided transfer.
- Explain faster evidence collection, reduced manual navigation, and more consistent investigation—not financial estimates.
- Show the factual validation evidence: agentic scenarios `4/4`, domain tool suite `PASS`, synthetic data.

### Optional 4:15–4:45 · Show SCN004 recovery

- Select `SCN004` and start resolution.
- Show the failed primary lookup, failed retry, and successful alternate authorization lookup.
- Explain that the recovery is bounded and the recovered evidence remains attached to the case.

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

If a browser refresh resets the session, reselect `SCN001` and click **Start resolution**. Because the playback uses local validated fixtures, it does not require network access and should return immediately.
