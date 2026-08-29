[CmdletBinding()]
param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Continue"
$containerName = "onecall-n8n"
$evaluationWorkflowId = "51efaf7f-33dd-4879-8a4e-8fde1d471e81"
$evaluationUrl = "http://localhost:5678/workflow/$evaluationWorkflowId"
$verifyScript = Join-Path $PSScriptRoot "verify-agentic-env.ps1"
$requiredWorkflowIds = @(
    "0a008c40-222e-4dcc-ac73-86d025653572",
    "d2f15189-d8a2-4a2f-a6eb-ebe0cf5f5013",
    "41adbefe-7314-4c67-b9d7-34b86ceee453",
    $evaluationWorkflowId
)

function Show-ManualFallback {
    param(
        [Parameter(Mandatory)]
        [string]$Reason
    )

    Write-Warning $Reason
    Write-Host ""
    Write-Host "Evaluation workflow: $evaluationUrl"
    Write-Host 'Open the workflow and click "Execute Workflow" once.'

    if ($OpenBrowser) {
        Start-Process $evaluationUrl
    } else {
        Write-Host "Use -OpenBrowser to open this URL automatically."
    }

    exit 1
}

function ConvertFrom-N8nExecutionOutput {
    param(
        [Parameter(Mandatory)]
        [object[]]$Lines
    )

    $text = ($Lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    try {
        return $text | ConvertFrom-Json -ErrorAction Stop
    } catch {
        $lastBrace = $text.LastIndexOf("}")
        if ($lastBrace -lt 0) {
            return $null
        }

        $searchIndex = 0
        while ($searchIndex -lt $lastBrace) {
            $startBrace = $text.IndexOf("{", $searchIndex)
            if ($startBrace -lt 0 -or $startBrace -ge $lastBrace) {
                break
            }

            $candidate = $text.Substring(
                $startBrace,
                $lastBrace - $startBrace + 1
            )
            try {
                return $candidate | ConvertFrom-Json -ErrorAction Stop
            } catch {
                $searchIndex = $startBrace + 1
            }
        }
    }

    return $null
}

function Find-EvaluationSummary {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value -or $Value -is [string] -or $Value -is [ValueType]) {
        return $null
    }

    $suiteProperty = $Value.PSObject.Properties["suite"]
    $resultsProperty = $Value.PSObject.Properties["results"]
    if (
        $null -ne $suiteProperty -and
        $suiteProperty.Value -eq "OneCall AI Agentic Scenarios" -and
        $null -ne $resultsProperty
    ) {
        return $Value
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        foreach ($item in $Value) {
            $found = Find-EvaluationSummary -Value $item
            if ($null -ne $found) {
                return $found
            }
        }
        return $null
    }

    foreach ($property in $Value.PSObject.Properties) {
        $found = Find-EvaluationSummary -Value $property.Value
        if ($null -ne $found) {
            return $found
        }
    }

    return $null
}

& $verifyScript
if ($LASTEXITCODE -ne 0) {
    Write-Error "Agentic environment verification failed. Evaluation was not run."
    exit 1
}

foreach ($workflowId in $requiredWorkflowIds) {
    & docker exec $containerName n8n export:workflow "--id=$workflowId" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Required workflow id $workflowId is not installed in local n8n."
        exit 1
    }
}

$helpOutput = & docker exec $containerName n8n execute --help 2>&1
$helpExitCode = $LASTEXITCODE
$helpText = ($helpOutput | ForEach-Object { [string]$_ }) -join "`n"
if ($helpExitCode -ne 0 -or $helpText -notmatch "--id") {
    Show-ManualFallback -Reason (
        "This installed n8n Server CLI does not expose supported workflow execution."
    )
}

$executeArguments = @(
    "exec",
    "-e",
    "N8N_RUNNERS_BROKER_PORT=5689",
    $containerName,
    "n8n",
    "execute",
    "--id=$evaluationWorkflowId"
)
if ($helpText -match "--rawOutput") {
    $executeArguments += "--rawOutput"
}

$executionOutput = & docker @executeArguments 2>&1
$executionExitCode = $LASTEXITCODE
if ($executionExitCode -ne 0) {
    Show-ManualFallback -Reason (
        "The local n8n CLI could not execute the evaluation reliably. " +
        "No PASS/FAIL result was assumed."
    )
}

$execution = ConvertFrom-N8nExecutionOutput -Lines @($executionOutput)
if ($null -eq $execution) {
    Show-ManualFallback -Reason (
        "The evaluation command completed, but its output was not parseable JSON. " +
        "No PASS/FAIL result was assumed."
    )
}

$summary = Find-EvaluationSummary -Value $execution
if ($null -eq $summary) {
    Show-ManualFallback -Reason (
        "The evaluation command completed, but no final scenario summary was returned. " +
        "No PASS/FAIL result was assumed."
    )
}

Write-Host ""
Write-Host "OneCall AI Agentic Scenario Evaluation"
Write-Host ""

$scenarioOrder = @("SCN001", "SCN002", "SCN003", "SCN004")
$passed = 0
foreach ($scenarioId in $scenarioOrder) {
    $result = @(
        $summary.results |
            Where-Object { $_.scenario_id -eq $scenarioId }
    ) | Select-Object -First 1

    $status = "FAIL"
    if ($null -ne $result -and $result.passed -eq $true) {
        $status = "PASS"
        $passed += 1
    }
    Write-Host ("{0,-8} {1}" -f $scenarioId, $status)
}

$overallStatus = "FAIL"
if ($passed -eq $scenarioOrder.Count -and $summary.status -eq "PASS") {
    $overallStatus = "PASS"
}

Write-Host ""
Write-Host ("TOTAL    {0}/{1} {2}" -f $passed, $scenarioOrder.Count, $overallStatus)

if ($overallStatus -ne "PASS") {
    exit 1
}
exit 0
