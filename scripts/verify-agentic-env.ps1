[CmdletBinding()]
param(
    [switch]$LocalOnly
)

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$containerName = "onecall-n8n"
$script:CheckResults = [System.Collections.Generic.List[object]]::new()

function Add-CheckResult {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [bool]$Passed
    )

    $script:CheckResults.Add(
        [PSCustomObject]@{
            Name = $Name
            Passed = $Passed
        }
    )
}

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $envPath) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.*)$") {
            $value = $Matches[1].Trim()
            if (
                $value.Length -ge 2 -and
                (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                 ($value.StartsWith("'") -and $value.EndsWith("'")))
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            return $value.Trim()
        }
    }

    return $null
}

function Invoke-DockerProbe {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    & docker @Arguments *> $null
    return $LASTEXITCODE -eq 0
}

Write-Host ""
Write-Host "OneCall AI Agentic Environment Verification"
Write-Host ""

$envExists = Test-Path -LiteralPath $envPath -PathType Leaf
Add-CheckResult -Name ".env file" -Passed $envExists

$keyConfigured = $false
$modelConfigured = $false
if ($envExists) {
    $keyConfigured = -not [string]::IsNullOrWhiteSpace(
        (Get-DotEnvValue -Name "NEBIUS_API_KEY")
    )
    $modelConfigured = -not [string]::IsNullOrWhiteSpace(
        (Get-DotEnvValue -Name "NEBIUS_MODEL")
    )
}
Add-CheckResult -Name "NEBIUS_API_KEY" -Passed $keyConfigured
Add-CheckResult -Name "NEBIUS_MODEL" -Passed $modelConfigured

if (-not $LocalOnly) {
    $dockerAvailable = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)
    Add-CheckResult -Name "Docker CLI" -Passed $dockerAvailable

    $engineAvailable = $false
    if ($dockerAvailable) {
        $engineAvailable = Invoke-DockerProbe -Arguments @(
            "info",
            "--format",
            "{{.ServerVersion}}"
        )
    }
    Add-CheckResult -Name "Docker Engine" -Passed $engineAvailable

    $containerRunning = $false
    if ($engineAvailable) {
        $running = & docker inspect --format "{{.State.Running}}" $containerName 2>$null
        $containerRunning = (
            $LASTEXITCODE -eq 0 -and
            ($running -join "").Trim() -eq "true"
        )
    }
    Add-CheckResult -Name "n8n Container" -Passed $containerRunning

    $containerHasKey = $false
    $containerHasModel = $false
    $workflowMountAvailable = $false
    $agentWorkflowsAvailable = $false
    if ($containerRunning) {
        $containerHasKey = Invoke-DockerProbe -Arguments @(
            "exec",
            $containerName,
            "sh",
            "-c",
            'test -n "$NEBIUS_API_KEY"'
        )
        $containerHasModel = Invoke-DockerProbe -Arguments @(
            "exec",
            $containerName,
            "sh",
            "-c",
            'test -n "$NEBIUS_MODEL"'
        )
        $workflowMountAvailable = Invoke-DockerProbe -Arguments @(
            "exec",
            $containerName,
            "test",
            "-d",
            "/files/workflows"
        )

        $agentWorkflowsAvailable = $workflowMountAvailable
        foreach ($file in @(
            "orchestrator-agent.json",
            "resolution-agent.json",
            "main-orchestrator.json",
            "orchestrator-evaluation.json"
        )) {
            if (-not (Invoke-DockerProbe -Arguments @(
                "exec",
                $containerName,
                "test",
                "-f",
                "/files/workflows/$file"
            ))) {
                $agentWorkflowsAvailable = $false
                break
            }
        }
    }

    Add-CheckResult -Name "Nebius Key in Container" -Passed $containerHasKey
    Add-CheckResult -Name "Nebius Model in Container" -Passed $containerHasModel
    Add-CheckResult -Name "Workflow Mount" -Passed $workflowMountAvailable
    Add-CheckResult -Name "Agent Workflows" -Passed $agentWorkflowsAvailable
}

foreach ($result in $script:CheckResults) {
    $status = "FAIL"
    if ($result.Passed) {
        $status = "PASS"
    }
    Write-Host ("{0,-30} {1}" -f $result.Name, $status)
}

$failedChecks = @($script:CheckResults | Where-Object { -not $_.Passed })
Write-Host ""
if ($failedChecks.Count -eq 0) {
    Write-Host "STATUS: READY"
    exit 0
}

Write-Error (
    "STATUS: NOT READY. Configure or start: " +
    (($failedChecks | ForEach-Object { $_.Name }) -join ", ")
)
exit 1
