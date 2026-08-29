# OneCall AI n8n Domain Tools

## Files

- eligibility-tool.json
- benefits-tool.json
- claims-tool.json
- authorization-tool.json
- provider-tool.json

## Expected inputs

| Domain tool | Inputs |
|---|---|
| Eligibility | member_id |
| Benefits | plan_id, service_code |
| Claims | member_id, service_code |
| Authorization | member_id, service_code, service_date |
| Provider | provider_id |

## Import and test

The n8n UI/export format may include workflow identifiers. On the local n8n version used by this project, CLI import requires non-null top-level `id` and `versionId` values. Generated import-ready workflows therefore keep repository-stable UUIDs for both fields.

Do not regenerate these IDs casually after a workflow has been established. Repeated CLI import of the same file may conflict with the workflow ID that was imported previously, so the automated importer is intended for first-time or newly generated workflow imports.

1. Run `scripts/import-n8n-workflows.ps1` from the project root.
2. Confirm the imported workflow names in local n8n.
3. Keep the workflows unpublished and inactive.
4. Open the Domain Tools Automated Test Harness.
5. Select each imported sub-workflow once; its local call target is intentionally not embedded in the repository artifact.
6. Configure the expected test inputs.
7. Execute the harness and validate the returned JSON envelope.
