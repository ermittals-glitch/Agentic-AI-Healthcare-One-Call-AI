[CmdletBinding()]
param(
    [string[]]$Files = @(
        "benefits-tool.json",
        "claims-tool.json",
        "authorization-tool.json",
        "provider-tool.json",
        "domain-tools-automated-test-harness.json"
    ),

    [switch]$UpdateExisting,

    [switch]$Force
)

$ErrorActionPreference = "Stop"
$containerName = "onecall-n8n"
$workflowDirectory = "/files/workflows"
$localWorkflowDirectory = Join-Path (Split-Path -Parent $PSScriptRoot) "workflows"

function Stop-Import {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [int]$Imported = 0,

        [int]$Failed = 1
    )

    Write-Error $Message
    Write-Host ""
    Write-Host "Imported: $Imported"
    Write-Host "Failed: $Failed"
    exit 1
}

function Invoke-DockerCheck {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    & docker @Arguments *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-Import -Message $FailureMessage
    }
}

function Test-Uuid {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($Value -isnot [string] -or [string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    $parsedValue = [guid]::Empty
    return [guid]::TryParseExact($Value, "D", [ref]$parsedValue)
}

function Test-WorkflowId {
    param(
        [AllowNull()]
        [object]$Value
    )

    return (
        $Value -is [string] -and
        -not [string]::IsNullOrWhiteSpace($Value) -and
        $Value.Length -le 128 -and
        $Value -match '^[A-Za-z0-9_-]+$'
    )
}

Write-Host ""
Write-Host "OneCall AI n8n Workflow Import"
Write-Host ""

if ($Files.Count -eq 0) {
    Stop-Import -Message "At least one workflow JSON file is required."
}

$workflowIds = @{}
$workflowVersionIds = @{}
$workflowMetadata = @{}

foreach ($file in $Files) {
    $leafName = Split-Path -Leaf $file
    $validName = (
        -not [string]::IsNullOrWhiteSpace($file) -and
        $file -eq $leafName -and
        $file -notmatch "[\\/]" -and
        $file -notmatch "\.\." -and
        $file.EndsWith(".json", [System.StringComparison]::OrdinalIgnoreCase)
    )

    if (-not $validName) {
        Stop-Import -Message "Invalid workflow filename: $file"
    }

    $localPath = Join-Path $localWorkflowDirectory $file
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        Stop-Import -Message "Workflow file was not found: $localPath"
    }

    try {
        $workflow = Get-Content -LiteralPath $localPath -Raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Stop-Import -Message "$file is not CLI-import ready: invalid JSON. $($_.Exception.Message)"
    }

    $propertyNames = @($workflow.PSObject.Properties.Name)
    $missingId = (
        $propertyNames -notcontains "id" -or
        [string]::IsNullOrWhiteSpace([string]$workflow.id)
    )
    $missingVersionId = (
        $propertyNames -notcontains "versionId" -or
        [string]::IsNullOrWhiteSpace([string]$workflow.versionId)
    )
    if ($missingId -or $missingVersionId) {
        Stop-Import -Message "$file is not CLI-import ready: missing workflow id/versionId."
    }

    foreach ($requiredField in @("name", "nodes", "connections")) {
        if ($propertyNames -notcontains $requiredField -or $null -eq $workflow.$requiredField) {
            Stop-Import -Message "$file is not CLI-import ready: missing required top-level field '$requiredField'."
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$workflow.name)) {
        Stop-Import -Message "$file is not CLI-import ready: workflow name is empty."
    }

    if (-not (Test-WorkflowId -Value $workflow.id)) {
        Stop-Import -Message "$file is not CLI-import ready: workflow id is not a valid stable n8n identifier."
    }

    if (-not (Test-Uuid -Value $workflow.versionId)) {
        Stop-Import -Message "$file is not CLI-import ready: versionId is not a valid UUID."
    }

    $workflowIdKey = ([string]$workflow.id).ToLowerInvariant()
    if ($workflowIds.ContainsKey($workflowIdKey)) {
        Stop-Import -Message "Duplicate workflow id detected in $($workflowIds[$workflowIdKey]) and $file."
    }
    $workflowIds[$workflowIdKey] = $file

    $versionIdKey = ([string]$workflow.versionId).ToLowerInvariant()
    if ($workflowVersionIds.ContainsKey($versionIdKey)) {
        Stop-Import -Message "Duplicate versionId detected in $($workflowVersionIds[$versionIdKey]) and $file."
    }
    $workflowVersionIds[$versionIdKey] = $file
    $workflowMetadata[$file] = [PSCustomObject]@{
        Id = [string]$workflow.id
        Name = [string]$workflow.name
    }
}

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCommand) {
    Stop-Import -Message "Docker CLI was not found."
}

Invoke-DockerCheck -Arguments @("info", "--format", "{{.ServerVersion}}") -FailureMessage "Docker Engine is not responding."

$running = & docker inspect --format "{{.State.Running}}" $containerName 2>$null
if ($LASTEXITCODE -ne 0 -or ($running -join "").Trim() -ne "true") {
    Stop-Import -Message "Container $containerName is not running."
}

Invoke-DockerCheck -Arguments @("port", $containerName, "5678/tcp") -FailureMessage "Container port 5678 is not exposed."
Invoke-DockerCheck -Arguments @("exec", $containerName, "test", "-d", "/files/data") -FailureMessage "Synthetic data mount /files/data is unavailable."
Invoke-DockerCheck -Arguments @("exec", $containerName, "test", "-d", $workflowDirectory) -FailureMessage "Workflow mount $workflowDirectory is unavailable."
Invoke-DockerCheck -Arguments @("exec", $containerName, "test", "-d", "/home/node/.n8n") -FailureMessage "Persistent n8n storage /home/node/.n8n is unavailable."

foreach ($file in $Files) {

    Invoke-DockerCheck -Arguments @("exec", $containerName, "test", "-f", "$workflowDirectory/$file") -FailureMessage "Workflow file is unavailable inside the container: $file"
}

$existingWorkflowIds = @{}
foreach ($file in $Files) {
    $workflowId = $workflowMetadata[$file].Id
    & docker exec $containerName n8n export:workflow "--id=$workflowId" *> $null
    if ($LASTEXITCODE -eq 0) {
        $existingWorkflowIds[$workflowId] = $file
        if (-not $UpdateExisting) {
            Stop-Import -Message (
                "$file already exists in n8n with workflow id $workflowId. " +
                "Re-run with -UpdateExisting to overwrite that same stable workflow id in place."
            )
        }
    }
}

if ($UpdateExisting) {
    Write-Warning (
        "Stable workflow IDs already present in n8n will be overwritten in place. " +
        "Unrelated workflows are not deleted or modified."
    )
} else {
    Write-Warning (
        "This importer is intended for newly generated workflows. " +
        "Do not repeatedly import the same workflow unless you intentionally use -UpdateExisting."
    )
}

if (-not $Force) {
    $confirmation = Read-Host "Type IMPORT to continue"
    if ($confirmation -cne "IMPORT") {
        Write-Host "Import cancelled. No workflows were imported."
        exit 0
    }
}

$imported = 0
foreach ($file in $Files) {
    Write-Host ""
    $workflowId = $workflowMetadata[$file].Id
    if ($existingWorkflowIds.ContainsKey($workflowId)) {
        Write-Host "Updating $file..."
    } else {
        Write-Host "Importing $file..."
    }

    & docker exec $containerName n8n import:workflow "--input=$workflowDirectory/$file"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL"
        Stop-Import -Message "Import failed for $file. Remaining imports were not attempted." -Imported $imported -Failed 1
    }

    $imported += 1
    Write-Host "PASS"
}

Write-Host ""
Write-Host "Imported: $imported"
Write-Host "Failed: 0"
exit 0
