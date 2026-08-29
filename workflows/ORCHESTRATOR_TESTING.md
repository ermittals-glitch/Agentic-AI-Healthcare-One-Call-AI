# OneCall AI Orchestrator Testing

## Validation boundary

Repository validation is static and deterministic. It proves JSON shape, stable cross-workflow IDs, graph branches, scenario fixtures, enum parsers, retry fields, and preservation of trusted artifacts.

It does not prove Nebius availability, environment validity, model behavior, or n8n runtime compatibility. Those require runtime evaluation.

## Automated evaluation

After completing `ORCHESTRATOR_SETUP.md`, run:

```powershell
.\scripts\verify-agentic-env.ps1
.\scripts\run-orchestrator-evaluation.ps1
```

The setup script automatically publishes the eight stored sub-workflows required by the agentic runtime and restarts n8n before this test. n8n 2.x imports workflows as unpublished, so rerun setup after importing or updating these workflows. The evaluation workflow itself remains unpublished and is executed only as a manual/test workflow.

Publishing these local stored sub-workflows does not create public internet exposure; the evaluation reaches them through Execute Sub-workflow nodes inside the local n8n instance.

The evaluation script verifies the four installed agentic workflow IDs, uses the supported self-hosted `n8n execute --id` command, captures output, and prints each scenario plus the total. It never assumes PASS when execution or parsing fails.

For a privacy-safe chronological trace, enable `ONECALL_DEBUG_TRACE=true`, rerun setup so Compose refreshes the container, and run:

```powershell
.\scripts\show-agentic-trace.ps1 -ScenarioId SCN001
```

The evaluator returns `debug_trace` and `first_error_event` only when tracing is enabled. The trace viewer prints whitelisted metadata and never prints prompts, raw model content, hidden reasoning, API keys, or Authorization headers. Restore the toggle to `false` and rerun setup after diagnosis.

If this installed n8n CLI cannot execute the workflow reliably, run:

```powershell
.\scripts\run-orchestrator-evaluation.ps1 -OpenBrowser
```

The browser fallback leaves one manual action: click **Execute Workflow** once.

The evaluator always runs all four cases and returns:

```json
{
  "suite": "OneCall AI Agentic Scenarios",
  "status": "PASS",
  "total": 4,
  "passed": 4,
  "failed": 0,
  "results": []
}
```

Individual assertion failures are accumulated rather than thrown.

## Required scenario evidence

### SCN001

- Root cause: `AUTHORIZATION_CLAIM_LOCATION_MISMATCH`
- Action: `CLAIM_RECONSIDERATION`
- Provider called
- No member transfer

### SCN002

- Root cause: `PRIOR_AUTHORIZATION_MISSING`
- Action: `PROVIDER_INITIATE_AUTHORIZATION`
- Provider not called
- No member transfer

### SCN003

- Root cause: `ELIGIBILITY_ENROLLMENT_MISMATCH`
- Action: `ELIGIBILITY_RECORD_REVIEW`
- Claims, Authorization, and Provider not called

### SCN004

- Root cause: `AUTHORIZATION_CLAIM_LINK_FAILURE`
- Action: `CLAIM_RECONSIDERATION`
- At least two Authorization errors
- At least two primary attempts recorded
- Alternate lookup used
- Eventual Authorization Tool status `SUCCESS`

## Troubleshooting

- A parser-generated human escalation usually indicates non-JSON output or an invalid enum.
- An environment verification failure means `.env` is incomplete or the Compose container has not been refreshed.
- An inference authorization failure means `NEBIUS_API_KEY` is missing or invalid; verification never prints it.
- A model error means `NEBIUS_MODEL` is missing or the selected model is unavailable.
- A workflow-reference or "Workflow is not active" error means the referenced stable workflow was not imported and published in the same n8n instance; rerun `setup-agentic-layer.ps1`.

Because model behavior is non-deterministic even at temperature zero, do not claim runtime success until the evaluation result is observed in n8n.
