# OneCall AI Loom script

## 3–5 minute natural walkthrough

Hi, this is OneCall AI, a healthcare payer resolution copilot for member-service representatives.

The problem I focused on is simple to describe but painful in practice. A member might call about a denied claim, but the answer can depend on eligibility, benefits, prior authorization, the claim record, and provider information. A representative may have to move between several systems, and the member may be transferred or asked to explain the same problem again.

OneCall AI changes that experience. The member explains the problem once. The system keeps that context in a shared case state, coordinates the investigation across payer systems, and gives the representative evidence-backed next steps.

At the top, this looks like a real call-center intake. I can choose Call or Chat, select one of four validated synthetic scenarios, and review the member ID, service, date, and inquiry. The data is synthetic, so no real member information is used.

I’m going to use scenario four because it shows both the normal workflow and failure recovery. The member says the claim was denied, but the authorization system is not responding. The intake note captures that concern once, while the request-flow diagram on the right shows how the same context moves through the system. The member does not have to repeat the story as the investigation crosses payer domains.

I’ll click Start resolution.

Now the orchestration section shows the complete path: intake, the orchestrator, payer-system checks, evidence synthesis, and the final recommendation. In the detailed trace, OneCall AI verifies coverage and benefits, reviews the claim denial, and then checks authorization.

For this scenario, the primary authorization lookup fails. The orchestrator retries once, that retry also fails, and then it deliberately switches to an alternate lookup using the member, service, and date. The alternate route finds the approved authorization. This is a bounded recovery strategy—not an open-ended retry loop—and the previous evidence stays in shared state.

The architecture diagram explains what is happening behind the console. The request enters once through Streamlit. The Main Orchestrator maintains shared case state. The Orchestrator Agent chooses one allowed next step, and the five deterministic domain tools return payer facts for eligibility, benefits, claims, authorization, and provider information. Once enough evidence is available, a separate Resolution Agent synthesizes the result. The final outcome returns to the representative for approval or human review.

That separation is important: the language model does not invent payer facts. The tool layer is deterministic, agent decisions are constrained, outputs are enum-validated, and a human remains in control of any action.

In the final resolution panel, the root cause is an authorization-claim link failure. The primary and retry paths failed, but alternate lookup found an approved authorization, while the denied claim had no authorization reference. The recommended next action is claim reconsideration.

The representative can see the workflow status, the supporting evidence, whether human approval is required, and whether the member needs to be transferred. Here, no member transfer is required. I can approve the recommendation or escalate the complete case context to a specialist. Either way, this prototype does not write to a payer system; it demonstrates the human decision boundary.

The operational value is intentionally presented without assumed dollar savings. The value is fewer transfers, less repeated storytelling, faster evidence gathering, lower manual navigation across systems, and more consistent resolution handling.

Finally, the validation panel shows the factual project evidence: the agentic evaluation passed all four scenarios, and the deterministic payer-domain suite passed. This polished demo uses those same validated synthetic fixtures, so it remains dependable without requiring a live external model call during the presentation.

That is OneCall AI: the member explains the problem once, the system coordinates the investigation, and the representative gets an evidence-backed path forward with human control preserved.
