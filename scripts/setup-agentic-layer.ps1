[CmdletBinding()]
param(
    [switch]$RunEvaluation
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$verifyScript = Join-Path $PSScriptRoot "verify-agentic-env.ps1"
$importScript = Join-Path $PSScriptRoot "import-n8n-workflows.ps1"
$evaluationScript = Join-Path $PSScriptRoot "run-orchestrator-evaluation.ps1"
$containerName = "onecall-n8n"
$managedWorkflowFiles = @(
    "eligibility-tool.json",
    "benefits-tool.json",
    "claims-tool.json",
    "authorization-tool.json",
    "provider-tool.json",
    "orchestrator-agent.json",
    "resolution-agent.json",
    "main-orchestrator.json",
    "orchestrator-evaluation.json"
)
$runtimeWorkflowFiles = @(
    "eligibility-tool.json",
    "benefits-tool.json",
    "claims-tool.json",
    "authorization-tool.json",
    "provider-tool.json",
    "orchestrator-agent.json",
    "resolution-agent.json",
    "main-orchestrator.json"
)
$evaluationWorkflowFile = "orchestrator-evaluation.json"

function Stop-Setup {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Error $Message
    exit 1
}

function Get-WorkflowIdentity {
    param(
        [Parameter(Mandatory)]
        [string]$FileName
    )

    $workflowPath = Join-Path (Join-Path $projectRoot "workflows") $FileName
    if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
        Stop-Setup -Message "Required workflow JSON was not found: $FileName"
    }

    try {
        $workflow = Get-Content -LiteralPath $workflowPath -Raw | ConvertFrom-Json
    } catch {
        Stop-Setup -Message "Required workflow JSON could not be parsed: $FileName"
    }

    if (
        [string]::IsNullOrWhiteSpace([string]$workflow.name) -or
        [string]::IsNullOrWhiteSpace([string]$workflow.id) -or
        [string]::IsNullOrWhiteSpace([string]$workflow.versionId)
    ) {
        Stop-Setup -Message "Required workflow JSON must contain non-empty name, id, and versionId fields: $FileName"
    }

    [pscustomobject]@{
        FileName = $FileName
        Name = [string]$workflow.name
        DisplayName = ([string]$workflow.name -replace '^OneCall AI - ', '')
        Id = [string]$workflow.id
        VersionId = [string]$workflow.versionId
    }
}

function Get-InstalledWorkflowVersionId {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Workflow
    )

    $metadataPath = "/tmp/onecall-workflow-metadata.json"
    & docker exec $containerName n8n export:workflow "--id=$($Workflow.Id)" "--output=$metadataPath" *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-Setup -Message "Could not export the imported workflow revision for $($Workflow.Name)."
    }

    $versionOutput = @(
        & docker exec $containerName node -e (
            "const data=require('$metadataPath');" +
            "const workflow=Array.isArray(data)?data[0]:data;" +
            "process.stdout.write(String(workflow.versionId||''));"
        ) 2>&1
    )
    $versionId = ($versionOutput -join "").Trim()
    $parsedVersionId = [guid]::Empty
    if (
        $LASTEXITCODE -ne 0 -or
        -not [guid]::TryParseExact($versionId, "D", [ref]$parsedVersionId)
    ) {
        Stop-Setup -Message "Imported workflow version verification failed for $($Workflow.Name)."
    }

    return $versionId
}

Write-Host ""
Write-Host "OneCall AI Agentic Layer Setup"
Write-Host ""

& $verifyScript -LocalOnly
if ($LASTEXITCODE -ne 0) {
    Stop-Setup -Message "Local .env configuration is incomplete. No Docker changes were made."
}

if ($null -eq (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-Setup -Message "Docker CLI was not found."
}

Write-Host "Refreshing the Compose-managed n8n container so .env values are loaded..."
Push-Location $projectRoot
try {
    & docker compose up -d --force-recreate n8n
    if ($LASTEXITCODE -ne 0) {
        Stop-Setup -Message "Docker Compose could not refresh the n8n container."
    }
} finally {
    Pop-Location
}

& $verifyScript
if ($LASTEXITCODE -ne 0) {
    Stop-Setup -Message "Agentic environment verification failed after Compose refresh."
}

& $importScript -Files $managedWorkflowFiles -UpdateExisting -Force
if ($LASTEXITCODE -ne 0) {
    Stop-Setup -Message "Agentic workflow import/update failed."
}

$runtimeWorkflows = @(
    $runtimeWorkflowFiles | ForEach-Object {
        Get-WorkflowIdentity -FileName $_
    }
)
if (
    $runtimeWorkflows.Count -ne 8 -or
    @($runtimeWorkflows.Id | Sort-Object -Unique).Count -ne 8
) {
    Stop-Setup -Message "Runtime publication requires exactly eight unique workflow IDs."
}

$evaluationWorkflow = Get-WorkflowIdentity -FileName $evaluationWorkflowFile
$publishedCount = 0
foreach ($workflow in $runtimeWorkflows) {
    Write-Host -NoNewline "Publishing $($workflow.DisplayName)... "
    $installedVersionId = Get-InstalledWorkflowVersionId -Workflow $workflow
    $publishOutput = @(
        & docker exec $containerName n8n publish:workflow "--id=$($workflow.Id)" "--versionId=$installedVersionId" 2>&1
    )
    $publishExitCode = $LASTEXITCODE
    $publishText = $publishOutput -join [Environment]::NewLine
    $alreadyPublished = $publishText -match '(?i)already\s+(published|active)'

    if ($publishExitCode -ne 0 -and -not $alreadyPublished) {
        Write-Host "FAIL"
        Stop-Setup -Message "Publishing $($workflow.Name) failed. $publishText"
    }

    Write-Host "PASS"
    $publishedCount++
}

Write-Host "Restarting n8n so the running service reloads imported and published workflow records..."
Push-Location $projectRoot
try {
    & docker compose restart n8n
    if ($LASTEXITCODE -ne 0) {
        Stop-Setup -Message "n8n could not be restarted after workflow publication."
    }
} finally {
    Pop-Location
}

& $verifyScript
if ($LASTEXITCODE -ne 0) {
    Stop-Setup -Message "Agentic environment verification failed after publication."
}

$verificationWorkflows = @($runtimeWorkflows)
$verificationWorkflows += $evaluationWorkflow
$workflowReady = [ordered]@{}
foreach ($workflow in $verificationWorkflows) {
    & docker exec $containerName n8n export:workflow "--id=$($workflow.Id)" *> $null
    $workflowReady[$workflow.DisplayName] = $LASTEXITCODE -eq 0
}

if (@($workflowReady.GetEnumerator() | Where-Object { -not $_.Value }).Count -gt 0) {
    $missing = @(
        $workflowReady.GetEnumerator() |
            Where-Object { -not $_.Value } |
            ForEach-Object { $_.Key }
    )
    Stop-Setup -Message (
        "Imported workflow verification failed: " + ($missing -join ", ")
    )
}

$exportHelp = @(& docker exec $containerName n8n export:workflow --help 2>&1)
$publishedExportSupported = (
    $LASTEXITCODE -eq 0 -and
    ($exportHelp -join [Environment]::NewLine) -match '(?m)--published\b'
)
if ($publishedExportSupported) {
    foreach ($workflow in $runtimeWorkflows) {
        & docker exec $containerName n8n export:workflow "--id=$($workflow.Id)" --published *> $null
        if ($LASTEXITCODE -ne 0) {
            Stop-Setup -Message "Published-state verification failed: $($workflow.Name)"
        }
    }
    Write-Host "Published-state verification: PASS"
} else {
    Write-Host "Published-state export verification is unavailable in this CLI; runtime evaluation is the final proof."
}

Write-Host ""
Write-Host "Published runtime workflows: $publishedCount"
Write-Host "Failed: 0"
Write-Host ""
Write-Host "Agentic layer setup complete."
Write-Host ""
foreach ($entry in $workflowReady.GetEnumerator()) {
    Write-Host ("{0,-26} READY" -f $entry.Key)
}

if ($RunEvaluation) {
    Write-Host ""
    & $evaluationScript
    exit $LASTEXITCODE
}

exit 0
