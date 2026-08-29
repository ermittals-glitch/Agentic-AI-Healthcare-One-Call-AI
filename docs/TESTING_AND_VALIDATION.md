# Testing and validation

## Validation strategy

OneCall AI uses layered validation so deterministic facts, orchestration behavior, and presentation behavior can be checked independently.

| Layer | Validation | Evidence |
|---|---|---|
| Synthetic fixtures | JSON data supports each declared scenario contract | Simulator raises on missing or conflicting records |
| Deterministic demo | Python unit tests assert root causes, routing, recovery, actions, and no writes | `10/10` simulator tests pass in the final UI pass |
| Domain tools | n8n harness checks eligibility, benefits, claims, authorization, and provider outputs | Previously runtime-validated `PASS` |
| Agentic orchestration | n8n evaluation asserts all four scenario outcomes and routing constraints | Previously runtime-validated `PASS 4/4` |
| Streamlit presentation | Compilation and Streamlit AppTest exercise initial and resolved renders | No uncaught exceptions in the final UI pass |
| Configuration and docs | TOML parse, link/path review, secret-pattern scan, and repository status | Included in final validation checklist |

## Deterministic simulator tests

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover:

- `SCN001` location mismatch and Provider Agent use;
- `SCN002` missing authorization and Provider Agent avoidance;
- `SCN003` eligibility/enrollment mismatch;
- `SCN004` recorded lookup failures, alternate recovery, and claim-link failure;
- a recommended action for every scenario;
- confirmation that no scenario performs an external write.

## Agentic evaluation contract

The n8n automated evaluation runs all scenarios and accumulates failures rather than stopping at the first one.

| Scenario | Expected root cause | Expected action | Additional assertion |
|---|---|---|---|
| `SCN001` | `AUTHORIZATION_CLAIM_LOCATION_MISMATCH` | `CLAIM_RECONSIDERATION` | Provider called; no member transfer |
| `SCN002` | `PRIOR_AUTHORIZATION_MISSING` | `PROVIDER_INITIATE_AUTHORIZATION` | Provider not called; no member transfer |
| `SCN003` | `ELIGIBILITY_ENROLLMENT_MISMATCH` | `ELIGIBILITY_RECORD_REVIEW` | Claims, Authorization, and Provider not called |
| `SCN004` | `AUTHORIZATION_CLAIM_LINK_FAILURE` | `CLAIM_RECONSIDERATION` | Two failures, two attempts, alternate used, eventual authorization success |

The previously observed final summary is `PASS`, total `4`, passed `4`, failed `0`. That result is prior runtime evidence; the final UI polish did not rerun Docker, n8n, or Nebius.

To deliberately refresh runtime evidence in a configured local environment:

```powershell
.\scripts\verify-agentic-env.ps1
.\scripts\run-orchestrator-evaluation.ps1
```

This may invoke the configured external model. Do not report a refreshed pass unless the evaluator prints the result.

## Streamlit validation

The final presentation checks cover:

- clean initial render with Call/Chat intake and all four scenario options;
- scenario-driven member, service code, service date, and inquiry fields;
- resolved render with orchestration trace, Mermaid architecture, evidence, and approval actions;
- `SCN004` retry and alternate-lookup recovery visibility;
- representative approval and escalation UI state;
- absence of payer writes and real member data.

Manual review remains appropriate for responsive layout, Mermaid legibility, and the complete 3–5 minute demo story.

## Security validation boundary

- `.env` is ignored and must never be printed or committed.
- `.env.example` contains names only and is safe to commit.
- Workflow JSON references environment variables rather than literal keys.
- The UI has no secret dependency and displays only synthetic fixture evidence.
- Trace output is opt-in and restricted to whitelisted metadata.
- No raw model prompt, raw response, Authorization header, API key, or hidden reasoning belongs in screenshots or submission artifacts.
