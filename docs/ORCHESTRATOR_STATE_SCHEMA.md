# OneCall AI Orchestrator State Schema

The Main Orchestrator passes one mutable `case_state` object through every decision and deterministic tool step. The object is returned as the final workflow output.

## Fields

| Field | Type | Initial value | Purpose |
|---|---|---|---|
| `case_id` | string | derived | Stable case label for the execution |
| `scenario_id` | string | input | Synthetic scenario selector |
| `member_id` | string | input | Member lookup key |
| `member_inquiry` | string | input | Member's stated issue |
| `service_code` | string/null | input | Service lookup key |
| `service_date` | string/null | input | Date of service; Claims may populate it |
| `plan_id` | string/null | null | Eligibility populates the member plan |
| `workflow_status` | enum | `INVESTIGATING` | Current lifecycle state |
| `iteration` | integer | 0 | Orchestrator loop counter |
| `max_iterations` | integer | 8 | Hard loop bound |
| `eligibility` | object/null | null | Eligibility Tool envelope |
| `benefits` | object/null | null | Benefits Tool envelope |
| `claim` | object/null | null | Claims Tool envelope |
| `authorization` | object/null | null | Authorization Tool envelope |
| `provider` | object/null | null | Provider Tool envelope |
| `agents_called` | array | [] | Ordered decision/tool/agent activity labels |
| `tool_calls` | array | [] | Tool, status, attempt, and iteration records |
| `tool_errors` | array | [] | Structured recoverable and terminal errors |
| `authorization_attempt_count` | integer | 0 | Primary Authorization attempt state |
| `authorization_alternate_used` | boolean | false | Alternate strategy marker |
| `root_cause` | enum/null | null | Validated Resolution Agent result |
| `recommended_action` | enum/null | null | Validated next best action |
| `member_transfer_required` | boolean/`UNKNOWN` | `UNKNOWN` | Transfer recommendation |
| `human_approval_required` | boolean | false | Transactional approval boundary |
| `human_handoff_reason` | string/null | null | Representative-facing reason |
| `final_resolution` | object/null | null | Complete Resolution Agent result |

## Status values

- `INVESTIGATING`
- `RESOLVED`
- `AWAITING_HUMAN_APPROVAL`
- `HUMAN_REVIEW_REQUIRED`

The guard internally marks an over-limit case for escalation and the terminal node returns `HUMAN_REVIEW_REQUIRED`.

## Invariants

- The loop increments `iteration` before every Orchestrator Agent call.
- If `iteration > 8`, no further AI or payer tool is called.
- Successful tool envelopes are retained without changing their payer facts.
- The SCN004 failure injection exists only in the Main Orchestrator.
- Two SCN004 primary failures are recorded before alternate lookup.
- No workflow performs a payer write.
- Recommended transactional actions always set `human_approval_required=true`.
- Agent parse failures safely terminate in human review.
