[CmdletBinding()]
param(
    [ValidateSet("SCN001", "SCN002", "SCN003", "SCN004")]
    [string]$ScenarioId = "SCN001"
)

$ErrorActionPreference = "Continue"
$containerName = "onecall-n8n"
$evaluationWorkflowId = "51efaf7f-33dd-4879-8a4e-8fde1d471e81"

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

            $candidate = $text.Substring($startBrace, $lastBrace - $startBrace + 1)
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

    if (
        $null -ne $Value.PSObject.Properties["suite"] -and
        $Value.suite -eq "OneCall AI Agentic Scenarios" -and
        $null -ne $Value.PSObject.Properties["results"]
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

$executionOutput = & docker exec `
    -e N8N_RUNNERS_BROKER_PORT=5689 `
    $containerName `
    n8n execute "--id=$evaluationWorkflowId" --rawOutput 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "The local n8n CLI could not execute the evaluation."
    exit 1
}

$execution = ConvertFrom-N8nExecutionOutput -Lines @($executionOutput)
$summary = Find-EvaluationSummary -Value $execution
if ($null -eq $summary) {
    Write-Error "No parseable evaluation summary was returned."
    exit 1
}

Write-Host ""
Write-Host "OneCall AI Evaluation Results"
Write-Host ""
foreach ($result in @($summary.results)) {
    $status = if ($result.passed -eq $true) { "PASS" } else { "FAIL" }
    $failureText = if (@($result.failures).Count -gt 0) {
        @($result.failures) -join "; "
    } else {
        "none"
    }
    Write-Host ("{0,-8} {1,-4} failures={2}" -f $result.scenario_id, $status, $failureText)
}

$scenario = @($summary.results | Where-Object { $_.scenario_id -eq $ScenarioId }) |
    Select-Object -First 1
if ($null -eq $scenario) {
    Write-Error "The evaluation did not return $ScenarioId."
    exit 1
}

$traceProperty = $scenario.PSObject.Properties["debug_trace"]
if ($null -eq $traceProperty) {
    Write-Error (
        "No debug trace was returned. Set ONECALL_DEBUG_TRACE=true, " +
        "rerun setup-agentic-layer.ps1, and try again."
    )
    exit 1
}

Write-Host ""
Write-Host "OneCall AI Agentic Trace - $ScenarioId"
Write-Host ""
foreach ($entry in @($traceProperty.Value)) {
    $details = $entry.details | ConvertTo-Json -Depth 8 -Compress
    Write-Host (
        "{0,3}  iter={1,-2} {2,-22} {3,-34} {4,-8} {5}" -f
        $entry.seq,
        $entry.iteration,
        $entry.component,
        $entry.event,
        $entry.status,
        $details
    )
}

Write-Host ""
if ($null -ne $scenario.first_error_event) {
    Write-Host (
        "First error: seq={0} component={1} event={2}" -f
        $scenario.first_error_event.seq,
        $scenario.first_error_event.component,
        $scenario.first_error_event.event
    )
} else {
    Write-Host "First error: none"
}

exit 0
