# Deployment validation

## Deployment model

The final submission has two local execution surfaces:

1. **Streamlit demo:** a secret-free controlled playback console using repository synthetic fixtures.
2. **n8n reference runtime:** a Docker-based agentic workflow using locally configured Nebius credentials.

The Streamlit demo is the recommended presentation surface. The n8n runtime remains available for explicit workflow evaluation but is not required to deliver the front-end demo.

## Final readiness snapshot

| Area | Status | Evidence |
|---|---|---|
| Streamlit source compilation | Ready | `streamlit_app.py` compiles |
| Streamlit initial render | Ready | AppTest completes with no uncaught exception |
| Resolved-case render | Ready | Start Resolution exposes resolution and approval controls |
| Four controlled scenarios | Ready | All four simulator contracts pass |
| Architecture visualization | Ready | Native `st.mermaid_chart` is present in the rendered app |
| Deterministic simulator tests | Ready | `10/10` pass |
| Deterministic n8n tool suite | Previously validated | Prior result `PASS` |
| Agentic n8n evaluation | Previously validated | Prior result `PASS 4/4` |
| Live n8n state in this polish pass | Not re-probed | Backend treated as stable; no Docker, n8n, or Nebius execution performed |
| Secret handling | Ready | UI requires no secret; `.env` remains ignored |

## Run the demo locally

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

If no virtual environment exists yet:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Expected result:

- Streamlit prints a local URL, normally `http://localhost:8501`.
- The initial app shows the OneCall AI header with intake and the architecture/request-flow diagram side by side.
- Clicking **Start resolution** reveals Case orchestration first, followed by the resolution, supporting evidence, operational value, validation evidence, and representative controls.

## Validate the front end

```powershell
.\.venv\Scripts\python.exe -m py_compile streamlit_app.py demo\simulator.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Manually check:

- switch between `SCN001` through `SCN004`;
- run each scenario and compare its root cause and action with `data/scenarios.json`;
- confirm `SCN004` shows two errors and alternate lookup recovery;
- approve and escalate a case, confirming only UI state changes;
- confirm the Mermaid diagram is legible at the presentation viewport;
- confirm no real member data, API keys, headers, prompts, or raw model content appear.

## Optional n8n verification

Only run this when the local environment is intentionally configured and external model execution is acceptable:

```powershell
docker compose up -d
.\scripts\verify-agentic-env.ps1
.\scripts\setup-agentic-layer.ps1
.\scripts\run-orchestrator-evaluation.ps1
```

Expected runtime evidence is an explicit four-scenario summary with status `PASS`, total `4`, passed `4`, and failed `0`. Treat any new output as the source of truth.

## Secret-safe configuration checklist

- [ ] Create local `.env` only from `.env.example`.
- [ ] Keep `.env` ignored and out of screenshots, logs, commits, and demos.
- [ ] Store no API key or bearer literal in Python, Markdown, JSON, or TOML.
- [ ] Keep Streamlit playback independent of secrets.
- [ ] Keep `ONECALL_DEBUG_TRACE=false` except during a bounded diagnostic session.
- [ ] Restore tracing to false after diagnostics.
- [ ] Never include raw model prompts, raw responses, or Authorization headers in submission evidence.

## Submission checklist

- [x] Professional call-center console
- [x] One-time member explanation
- [x] Visible orchestrated investigation path
- [x] Static component/request-flow diagram
- [x] Scenario-specific path and `SCN004` recovery visibility
- [x] Evidence-backed root cause and next action
- [x] Human approval and escalation boundary
- [x] Non-monetary operational value
- [x] Factual `4/4` validation evidence
- [x] README, architecture, test, deployment, demo, and Loom documentation
- [x] No backend workflow rewrite during final polish

## Deployment limitations

The repository is submission-ready as a local prototype, not as a production healthcare deployment. Production use would require authentication, authorization, PHI safeguards, audit retention, observability, governed integrations, availability controls, and organizational compliance review.
