# Final project summary

## Product overview

OneCall AI is a healthcare payer resolution copilot designed for member-service representatives. A member explains a coverage, claim, authorization, or eligibility problem once. The system keeps that context in shared case state, coordinates evidence gathering across payer domains, and returns a clear root cause and next action to the representative.

The project is a bounded Agentic AI prototype built entirely with synthetic data. It demonstrates decision support and human-controlled workflow recommendations; it does not provide medical advice or update payer records.

## Problem solved

Payer-service inquiries rarely fit inside one system. A denial can require eligibility, benefit, claim, authorization, and provider evidence before a representative can explain what happened. Without coordination, the representative performs manual cross-system navigation while the member may be transferred or asked to repeat the same issue.

OneCall AI turns that fragmented investigation into one guided interaction:

- the member concern is captured once;
- relevant payer-system checks are orchestrated against shared context;
- the representative sees the path and supporting evidence;
- a bounded Resolution Agent recommends the next action;
- a human retains control of any action or escalation.

## Primary personas

### Member-service representative

Uses the console during a call or chat, reviews the evidence-backed recommendation, and approves or escalates the next step.

### Member

Provides the concern once and remains with the same servicing interaction while the system coordinates the investigation.

### Payer operations or quality lead

Reviews consistent investigation paths, human-review boundaries, and scenario validation evidence.

### Workflow engineer

Maintains stable n8n workflow definitions, deterministic domain tools, constrained agent decisions, and evaluation contracts.

## End-to-end solution

1. **Interaction intake:** Streamlit captures channel, scenario, member, service, date, and the member inquiry.
2. **Shared state initialization:** The Main Orchestrator creates one case record that survives each planning and tool step.
3. **Bounded planning:** The Orchestrator Agent selects one allowed next decision using only facts already in state.
4. **Deterministic checks:** Eligibility, Benefits, Claims, Authorization, and Provider workflows return synthetic payer facts.
5. **Recovery:** `SCN004` records two authorization lookup failures, then succeeds through the alternate lookup route.
6. **Evidence synthesis:** The Resolution Agent selects a validated root-cause and action enum and explains the evidence.
7. **Human boundary:** Recommendations that imply a payer action wait for representative approval. Approval changes the UI case to `READY_FOR_ACTION`; internal specialist escalation changes it to `HUMAN_REVIEW_REQUIRED` while preserving shared context.
8. **Representative view:** The console presents the consolidated result without asking the member to repeat the story.

## Final implementation state

- Five deterministic payer-domain tools are preserved.
- The Main Orchestrator, Orchestrator Agent, and Resolution Agent remain unchanged by the final UI pass.
- Four agentic scenarios previously passed runtime evaluation: `4/4`.
- The deterministic domain tool suite previously passed validation.
- The Streamlit demo now supports Call and Chat intake, all four scenarios, one-time inquiry capture, orchestration status, evidence, a functional human-decision state machine, operational value, and an embedded architecture diagram.
- All eight scenario/decision outcomes are explicit: four approval results and four internal specialist-review results. The unselected decision disappears after a choice, and the representative can clear only that choice without rerunning AI investigation.
- Controlled playback is intentionally used for the front-end demo so presentation does not depend on external model or local n8n availability.

## Operational value demonstrated

The project demonstrates reduced member repetition, fewer transfers, faster evidence gathering, lower manual navigation burden, consistent investigation steps, and stronger representative decision support. These are qualitative process benefits; no monetary savings or assumed ROI are claimed.

## Safety and privacy boundary

All repository data is synthetic. Secrets remain in an ignored local environment file and are not stored in workflow JSON. Debug tracing is opt-in and limited to whitelisted metadata. The UI does not display secrets, Authorization headers, model prompts, raw model responses, or hidden reasoning. Approval stages a recommendation only, and escalation prepares a shared-context evidence package only; neither path modifies a payer record.
