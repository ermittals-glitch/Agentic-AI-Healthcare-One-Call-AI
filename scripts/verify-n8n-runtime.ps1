[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$script:CheckResults = [System.Collections.Generic.List[object]]::new()

function Add-CheckResult {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [bool]$Passed,

        [string]$Detail = ""
    )

    $script:CheckResults.Add(
        [PSCustomObject]@{
            Name = $Name
            Passed = $Passed
            Detail = $Detail
        }
    )
}

function Invoke-DockerProbe {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    $output = & docker @Arguments 2>$null
    return [PSCustomObject]@{
        Passed = ($LASTEXITCODE -eq 0)
        Output = @($output)
    }
}

Write-Host ""
Write-Host "OneCall AI n8n Runtime Verification"
Write-Host ""

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerAvailable = $null -ne $dockerCommand
Add-CheckResult -Name "Docker CLI" -Passed $dockerAvailable

$engineAvailable = $false
if ($dockerAvailable) {
    $engineProbe = Invoke-DockerProbe -Arguments @("info", "--format", "{{.ServerVersion}}")
    $engineAvailable = $engineProbe.Passed
}
Add-CheckResult -Name "Docker Engine" -Passed $engineAvailable

$containerRunning = $false
if ($engineAvailable) {
    $containerProbe = Invoke-DockerProbe -Arguments @(
        "inspect",
        "--format",
        "{{.State.Running}}",
        "onecall-n8n"
    )
    $containerRunning = (
        $containerProbe.Passed -and
        ($containerProbe.Output -join "").Trim() -eq "true"
    )
}
Add-CheckResult -Name "onecall-n8n Container" -Passed $containerRunning

$portAvailable = $false
if ($containerRunning) {
    $portProbe = Invoke-DockerProbe -Arguments @(
        "port",
        "onecall-n8n",
        "5678/tcp"
    )
    $portAvailable = (
        $portProbe.Passed -and
        ($portProbe.Output -join " ") -match "5678"
    )
}
Add-CheckResult -Name "Port 5678" -Passed $portAvailable

$expectedDataFiles = @(
    "members.json",
    "benefits.json",
    "claims.json",
    "authorizations.json",
    "providers.json",
    "scenarios.json"
)
$dataMountAvailable = $false
if ($containerRunning) {
    $dataDirectoryProbe = Invoke-DockerProbe -Arguments @(
        "exec",
        "onecall-n8n",
        "test",
        "-d",
        "/files/data"
    )
    $dataMountAvailable = $dataDirectoryProbe.Passed

    if ($dataMountAvailable) {
        foreach ($file in $expectedDataFiles) {
            $fileProbe = Invoke-DockerProbe -Arguments @(
                "exec",
                "onecall-n8n",
                "test",
                "-f",
                "/files/data/$file"
            )
            if (-not $fileProbe.Passed) {
                $dataMountAvailable = $false
                break
            }
        }
    }
}
Add-CheckResult -Name "Synthetic Data Mount" -Passed $dataMountAvailable

$expectedWorkflowFiles = @(
    "n8n-smoke-test.json",
    "eligibility-tool.json",
    "eligibility-tool-test-caller.json",
    "benefits-tool.json",
    "claims-tool.json",
    "authorization-tool.json",
    "provider-tool.json",
    "domain-tools-automated-test-harness.json"
)
$workflowMountAvailable = $false
if ($containerRunning) {
    $workflowDirectoryProbe = Invoke-DockerProbe -Arguments @(
        "exec",
        "onecall-n8n",
        "test",
        "-d",
        "/files/workflows"
    )
    $workflowMountAvailable = $workflowDirectoryProbe.Passed

    if ($workflowMountAvailable) {
        foreach ($file in $expectedWorkflowFiles) {
            $fileProbe = Invoke-DockerProbe -Arguments @(
                "exec",
                "onecall-n8n",
                "test",
                "-f",
                "/files/workflows/$file"
            )
            if (-not $fileProbe.Passed) {
                $workflowMountAvailable = $false
                break
            }
        }
    }
}
Add-CheckResult -Name "Workflow Mount" -Passed $workflowMountAvailable

$persistentStorageAvailable = $false
if ($containerRunning) {
    $storageProbe = Invoke-DockerProbe -Arguments @(
        "exec",
        "onecall-n8n",
        "test",
        "-d",
        "/home/node/.n8n"
    )
    $persistentStorageAvailable = $storageProbe.Passed
}
Add-CheckResult -Name "Persistent n8n Storage" -Passed $persistentStorageAvailable

foreach ($result in $script:CheckResults) {
    $status = "FAIL"
    if ($result.Passed) {
        $status = "PASS"
    }
    Write-Host ("{0,-28} {1}" -f $result.Name, $status)
}

$failedChecks = @($script:CheckResults | Where-Object { -not $_.Passed })
Write-Host ""
if ($failedChecks.Count -eq 0) {
    Write-Host "STATUS: READY"
    exit 0
}

Write-Error (
    "STATUS: NOT READY. Failed checks: " +
    (($failedChecks | ForEach-Object { $_.Name }) -join ", ")
)
exit 1
