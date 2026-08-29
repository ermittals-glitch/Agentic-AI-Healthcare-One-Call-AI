# OneCall AI Orchestrator Setup

## Configure local environment

From the project root, create the ignored local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set both values:

```dotenv
NEBIUS_API_KEY=<your local key>
NEBIUS_MODEL=<currently available Nebius chat model>
```

Optional diagnostic tracing defaults off:

```dotenv
ONECALL_DEBUG_TRACE=false
```

Set it to `true` only for a bounded local diagnostic session. Compose forwards the value to n8n, and workflow code accepts `1`, `true`, `yes`, or `on` case-insensitively. Traces contain metadata only and must still be treated as local diagnostic artifacts.

Never commit `.env`, print its values, or paste the key into workflow JSON.

## Automated setup

Run:

```powershell
.\scripts\setup-agentic-layer.ps1
```

The script:

- validates the local `.env` without printing values;
- recreates the Compose-managed n8n container so the two variables are loaded;
- verifies the container environment and read-only workflow mount;
- imports new stable workflow IDs or overwrites the same IDs in place;
- reads workflow names and IDs from the five domain-tool and three runtime agentic JSON files;
- publishes those eight stored sub-workflows individually with the n8n 2.x CLI;
- restarts n8n so the running service reloads imported and published records;
- verifies the required workflow records and, when supported by the installed CLI, their published exports.

n8n 2.x imports workflows as unpublished. The setup script therefore publishes Eligibility Tool, Benefits Tool, Claims Tool, Authorization Tool, Provider Tool, Orchestrator Agent, Resolution Agent, and Main Orchestrator automatically. Publishing is safely repeatable, and an already-published result is treated as successful.

The Orchestrator Automated Evaluation is deliberately not published. It remains a manual/test workflow invoked by the evaluation script or from the local n8n editor. Publishing the eight stored sub-workflows does not expose them to the public internet; they execute inside the local n8n instance through Execute Sub-workflow nodes.

No n8n credential or per-workflow model selection is required. Both agents read `NEBIUS_MODEL` from the container environment and construct the Authorization header from `NEBIUS_API_KEY` at execution time. `ONECALL_DEBUG_TRACE` controls only the privacy-safe diagnostic trace and does not enter either AI request.

The Compose setting `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` is narrowly required for these workflow expressions. Only variables explicitly forwarded into the container are available; Compose does not pass the complete host environment.

## Run evaluation

Run:

```powershell
.\scripts\run-orchestrator-evaluation.ps1
```

The script uses the supported self-hosted Server CLI when available and parses the final four-scenario summary. If this installed n8n runtime cannot execute or expose parseable output, it prints the exact workflow URL. Add `-OpenBrowser` to open it and click **Execute Workflow** once.
