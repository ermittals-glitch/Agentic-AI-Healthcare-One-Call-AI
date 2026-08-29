# OneCall AI Local Automation

These scripts manage the local Docker-based n8n development environment without storing credentials in the repository.

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

Repeated CLI import of the same file may conflict with an already-imported workflow ID. Use the importer for first-time or newly generated workflow imports, not as a repeated synchronization command.

## Import future workflow files

    .\scripts\import-n8n-workflows.ps1 -Files @(
      "main-orchestrator.json",
      "orchestrator-evaluation.json"
    )

The n8n UI is available at:

    http://localhost:5678

The data and workflow directories are mounted read-only. Secrets must remain outside Git.

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
