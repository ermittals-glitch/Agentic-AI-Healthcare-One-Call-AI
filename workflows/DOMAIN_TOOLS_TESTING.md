# Automated Domain Tool Tests

## Purpose

Validate all five deterministic payer-domain tools before connecting them to the AI Orchestrator.

The harness runs 10 deterministic test cases in one execution and should produce a 10/10 PASS summary. It uses synthetic data only, contains no PHI, calls no LLM, and uses no external services.

## One-time n8n setup

1. Import all five domain workflow JSON files.
2. Import domain-tools-automated-test-harness.json.
3. Open each of the five Call nodes in the harness.
4. Select the corresponding imported workflow.
5. Verify that the displayed input fields retain their current-item mappings.
6. Confirm Run once for each item mode.
7. Confirm Wait for Sub-Workflow is enabled.
8. Save the harness while keeping it inactive.

The required tool selections are:

| Harness node | Imported workflow |
|---|---|
| Call Eligibility Tool | OneCall AI - Eligibility Tool |
| Call Benefits Tool | OneCall AI - Benefits Tool |
| Call Claims Tool | OneCall AI - Claims Tool |
| Call Authorization Tool | OneCall AI - Authorization Tool |
| Call Provider Tool | OneCall AI - Provider Tool |

## Run the suite

After the one-time setup:

1. Open OneCall AI - Domain Tools Automated Test Harness.
2. Select Execute Workflow.
3. Open the Build Test Summary output.
4. Confirm suite status is PASS with 10 passed and 0 failed.

Expected totals:

| Tool | Expected result |
|---|---|
| Eligibility | 3/3 PASS |
| Benefits | 2/2 PASS |
| Claims | 1/1 PASS |
| Authorization | 3/3 PASS |
| Provider | 1/1 PASS |
| Total | 10/10 PASS |
