# OneCall AI Agentic Workflow

## Design boundary

The five payer-domain workflows remain deterministic because eligibility, benefits, claims, authorization, and provider data are payer facts. An LLM must not generate those facts.

The Orchestrator Agent uses AI for bounded next-step selection. The separate Resolution Agent uses AI only after evidence gathering, keeping investigation planning separate from synthesis and recommendation.

## Flow

```text
Case Intake
  -> Initialize shared state
  -> Iteration guard
  -> Orchestrator Agent
  -> allowed decision router
      -> deterministic payer tool -> update state -> loop
      -> Resolution Agent -> structured recommendation
      -> Human review
```

All sub-workflows are referenced by repository-stable IDs. Model responses are JSON-only and enum-validated before routing.

## Dynamic routing

- SCN001 gathers Eligibility, Benefits, Claims, Authorization, and Provider evidence because claim and authorization locations conflict.
- SCN002 stops after Authorization returns `NOT_FOUND`; Provider is unnecessary and must be avoided.
- SCN003 uses Eligibility enrollment/synchronization facts and avoids Claims, Authorization, and Provider.
- SCN004 records two simulated Authorization failures, then uses the actual healthy Authorization Tool through an alternate route.

The exact order remains an AI runtime decision within the allowed decision set. Automated evaluation verifies the required evidence and tool-avoidance contracts.

## Shared state and bounded execution

Every step receives and updates the same documented case state. Tool calls, errors, attempts, evidence, and agent decisions survive loop iterations. A hard maximum of eight completed planning iterations prevents infinite loops.

## Failure recovery

SCN004 injects failure only in the Main Orchestrator:

1. First `CHECK_AUTHORIZATION`: record a simulated primary failure without calling the tool.
2. Second `CHECK_AUTHORIZATION`: record a simulated retry failure without calling the tool.
3. `CHECK_AUTHORIZATION_ALTERNATE`: mark alternate use and call the healthy Authorization Tool.
4. Return the successful evidence to the Orchestrator Agent.

Choosing another primary attempt after retries are exhausted terminates safely in human review.

## Human approval boundary

The workflow investigates and recommends; it never updates payer records. Claim reconsideration, provider authorization initiation, and eligibility record review end in `AWAITING_HUMAN_APPROVAL`. Invalid agent output or exhausted investigation ends in `HUMAN_REVIEW_REQUIRED`.

The existing Streamlit Approve/Escalate controls remain a later integration boundary.

## Data and privacy

The milestone uses only repository synthetic data. The only external request is LLM inference to the configured Nebius chat-completions endpoint. The API key remains in the ignored local `.env`, is forwarded only into the n8n container, and is read by the two inference-node expressions without entering workflow JSON or Git.

## Privacy-safe debug trace

Structured tracing is opt-in through `ONECALL_DEBUG_TRACE`. Its default is `false`. When enabled, the Main Orchestrator carries a chronological `debug_trace` through planning, deterministic tool calls, resolution, and escalation. The two AI workflows add request-configuration flags and response-envelope/parser metadata only.

Trace entries never contain API keys, Authorization headers, raw prompts, raw model responses, member inquiries, or hidden reasoning. Each entry is limited to sequence, timestamp, component, event, status, iteration, and whitelisted metadata such as presence flags, response keys, content length, enum-validation status, and route names.

The evaluator includes `debug_trace` and `first_error_event` per scenario only while tracing is enabled. Use `scripts/show-agentic-trace.ps1` to render a safe scenario trace. Disable the toggle and rerun setup after diagnosis to restore the normal concise output.

The AI HTTP nodes request `Accept-Encoding: identity` and use n8n response-format autodetection. This is required because the installed HTTP Request node streams responses when the request body is raw; autodetection resolves that stream and then parses the Token Factory `application/json` body before the workflow parser runs.
