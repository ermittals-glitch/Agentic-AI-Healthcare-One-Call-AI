# OneCall AI Local Automation

These scripts manage the local Docker-based n8n development environment without storing credentials in the repository.

## First-time agentic setup

Create the ignored local environment file and edit its two values:

    Copy-Item .env.example .env

Set `NEBIUS_API_KEY` and `NEBIUS_MODEL` in `.env`. Never commit `.env` and never paste the key into workflow JSON.

Then run:

    docker compose up -d
    .\scripts\verify-agentic-env.ps1
    .\scripts\setup-agentic-layer.ps1
    .\scripts\run-orchestrator-evaluation.ps1

`setup-agentic-layer.ps1` refreshes the Compose container, verifies the environment without printing the key, and creates or updates the four stable-ID agentic workflows. Because n8n 2.x imports workflows as unpublished, setup also reads the authoritative IDs from the five domain-tool and three runtime agentic workflow JSON files, publishes those eight stored sub-workflows individually, and restarts n8n before verification. Use `-RunEvaluation` to request evaluation immediately after setup.

The Orchestrator Automated Evaluation remains unpublished and is run only as a manual/test workflow. Publishing these stored sub-workflows in the local n8n instance does not create public internet exposure; they are invoked internally through Execute Sub-workflow nodes.

## Normal agentic development

After Codex generates or refines the AI workflow files, run:

    .\scripts\setup-agentic-layer.ps1
    .\scripts\run-orchestrator-evaluation.ps1

Change the Nebius model by editing `NEBIUS_MODEL` in `.env` and rerunning setup. Compose recreates the n8n container while preserving the external `onecall_n8n_data` volume.

Privacy-safe structured tracing is disabled by default. For a bounded local diagnostic session, set `ONECALL_DEBUG_TRACE=true`, rerun setup, and display one scenario with:

    .\scripts\show-agentic-trace.ps1 -ScenarioId SCN001

The helper prints only structured trace metadata. Restore `ONECALL_DEBUG_TRACE=false` and rerun setup when diagnosis is complete.

## Start n8n

    docker compose up -d

## Stop n8n

    docker compose stop

## Check status

    .\scripts\show-n8n-status.ps1

## Verify environment

    .\scripts\verify-n8n-runtime.ps1

## Import current generated workflows

    .\scripts\import-n8n-workflows.ps1

The importer warns about duplicate workflow records and requires typing IMPORT before it proceeds. Use -Force only when intentionally running without the confirmation prompt:

    .\scripts\import-n8n-workflows.ps1 -Force

The n8n UI/export format may carry workflow identifiers. The n8n CLI in this local environment requires non-null top-level `id` and `versionId` values, so generated import-ready workflows contain repository-stable UUIDs. Do not regenerate these IDs casually after a workflow has been established.

Without `-UpdateExisting`, the importer stops if a requested stable workflow ID already exists. With `-UpdateExisting`, n8n's supported same-ID import behavior overwrites that workflow in place without deleting unrelated workflows:

    .\scripts\import-n8n-workflows.ps1 -Files @(
      "orchestrator-agent.json",
      "resolution-agent.json",
      "main-orchestrator.json",
      "orchestrator-evaluation.json"
    ) -UpdateExisting

## Import future workflow files

    .\scripts\import-n8n-workflows.ps1 -Files @(
      "main-orchestrator.json",
      "orchestrator-evaluation.json"
    )

The n8n UI is available at:

    http://localhost:5678

The data and workflow directories are mounted read-only. Secrets must remain outside Git.

The AI workflows read only the explicitly forwarded `NEBIUS_API_KEY`, `NEBIUS_MODEL`, and `ONECALL_DEBUG_TRACE` container variables. `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` is required for n8n expressions to read them. This does not forward the rest of the host environment into the container. The only external AI request is sent to `https://api.tokenfactory.nebius.com/v1/chat/completions`.

The five payer-domain workflows remain deterministic. Nebius is used only for orchestration decisions and final evidence synthesis.

The external Docker volume onecall_n8n_data contains the persistent local n8n instance data and must never be deleted casually. Do not run docker compose down -v or delete this volume unless permanent data removal is explicitly intended.

## One-time migration from a manually created container

This process replaces only the existing container while preserving the external onecall_n8n_data volume.

1. Ensure all current n8n work is saved.
2. Stop the manually created container:

       docker stop onecall-n8n

3. Remove only that container:

       docker rm onecall-n8n

4. Do not delete the onecall_n8n_data volume.
5. Start the Compose-managed container:

       docker compose up -d

6. Verify the runtime:

       .\scripts\verify-n8n-runtime.ps1

Because docker-compose.yml declares onecall_n8n_data as an external volume, the Compose-managed container reuses the existing n8n owner account, configuration, and workflow data stored in that volume.
