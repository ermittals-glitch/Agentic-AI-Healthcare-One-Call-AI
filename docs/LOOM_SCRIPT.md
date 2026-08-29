# OneCall AI Loom script

## 3–5 minute natural walkthrough

Hi, this is OneCall AI, a healthcare payer resolution copilot for member-service representatives.

The problem I focused on is simple to describe but painful in practice. A member might call about a denied claim, but the answer can depend on eligibility, benefits, prior authorization, the claim record, and provider information. A representative may have to move between several systems, and the member may be transferred or asked to explain the same problem again.

OneCall AI changes that experience. The member explains the problem once. The system keeps that context in a shared case state, coordinates the investigation across payer systems, and gives the representative evidence-backed next steps.

At the top, this looks like a real call-center intake. I can choose Call or Chat, select one of four validated synthetic scenarios, and review the member ID, service, date, and inquiry. The data is synthetic, so no real member information is used.

I’m going to use scenario one: a claim was denied even though the provider says the authorization was approved. The intake note captures that concern once, while the request-flow diagram on the right shows how the same context moves through the system. The member does not have to repeat the story as the investigation crosses payer domains.

I’ll click Start resolution.

Now the orchestration section shows the complete path: intake, the orchestrator, payer-system checks, evidence synthesis, and the final recommendation. In the detailed trace, OneCall AI verifies coverage and benefits, reviews the denied claim, finds the approved authorization, and validates the provider organization and servicing locations. Every step builds on the same shared case evidence.

The architecture diagram explains what is happening behind the console. The request enters once through Streamlit. The Main Orchestrator maintains shared case state. The Orchestrator Agent chooses one allowed next step, and the five deterministic domain tools return payer facts for eligibility, benefits, claims, authorization, and provider information. Once enough evidence is available, a separate Resolution Agent synthesizes the result. The final outcome returns to the representative for approval or human review.

That separation is important: the language model does not invent payer facts. The tool layer is deterministic, agent decisions are constrained, outputs are enum-validated, and a human remains in control of any action.

In the final resolution panel, the root cause is an authorization-claim servicing-location mismatch. The claim and approved authorization point to different servicing locations, while provider validation confirms that both locations belong to the same in-network organization. The recommended next action is claim reconsideration.

The representative can see the workflow status, supporting evidence, and whether human approval or a member transfer is required. The AI has completed its work, but the case is still waiting at `AWAITING_HUMAN_APPROVAL`.

I’ll click Approve recommended action.

The two decision choices are now replaced by one explicit representative result. The decision is Approved, and the case status changes to `READY_FOR_ACTION`. The approved next step is claim reconsideration. The result also makes four boundaries clear: member transfer is No, the member does not repeat the issue, shared case context is preserved, and no payer record was modified.

This is the human-in-the-loop boundary. The AI investigates and recommends, the representative decides, and only then is the operational action ready. In a real implementation, an authenticated and governed payer integration would submit that action after approval. This prototype stages the recommendation only.

The operational value is intentionally presented without assumed dollar savings. The value is fewer transfers, less repeated storytelling, faster evidence gathering, lower manual navigation across systems, and more consistent resolution handling.

Finally, the validation panel shows the factual project evidence: the agentic evaluation passed all four scenarios, and the deterministic payer-domain suite passed. This polished demo uses those same validated synthetic fixtures, so it remains dependable without requiring a live external model call during the presentation.

That is OneCall AI: the member explains the problem once, the system coordinates the investigation, and the representative gets an evidence-backed path forward with human control preserved.
