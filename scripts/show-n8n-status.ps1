[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$containerName = "onecall-n8n"
$volumeName = "onecall_n8n_data"

function Write-StatusLine {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$Value
    )

    Write-Host ("{0,-22} {1}" -f $Name, $Value)
}

Write-Host ""
Write-Host "OneCall AI Local Environment"
Write-Host ""

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCommand) {
    Write-StatusLine -Name "Docker Desktop" -Value "UNAVAILABLE"
    Write-StatusLine -Name "Docker Engine" -Value "STOPPED"
    Write-StatusLine -Name "n8n Container" -Value "UNKNOWN"
    exit 1
}

Write-StatusLine -Name "Docker Desktop" -Value "AVAILABLE"

& docker info --format "{{.ServerVersion}}" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-StatusLine -Name "Docker Engine" -Value "STOPPED"
    Write-StatusLine -Name "n8n Container" -Value "UNKNOWN"
    exit 1
}

Write-StatusLine -Name "Docker Engine" -Value "RUNNING"

$containerJson = & docker inspect $containerName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-StatusLine -Name "n8n Container" -Value "NOT FOUND"
    $volumeExists = & docker volume inspect $volumeName 2>$null
    if ($LASTEXITCODE -eq 0 -and $volumeExists) {
        Write-StatusLine -Name "Persistent Volume" -Value $volumeName
    } else {
        Write-StatusLine -Name "Persistent Volume" -Value "NOT FOUND"
    }
    exit 1
}

$container = @($containerJson | ConvertFrom-Json)[0]
$runningStatus = "STOPPED"
if ($container.State.Running) {
    $runningStatus = "RUNNING"
}

$containerId = [string]$container.Id
if ($containerId.Length -gt 12) {
    $containerId = $containerId.Substring(0, 12)
}

$ports = & docker port $containerName 2>$null
$portText = "NOT EXPOSED"
if ($LASTEXITCODE -eq 0 -and @($ports).Count -gt 0) {
    $portText = (@($ports) -join ", ")
}

$mountDestinations = @($container.Mounts | ForEach-Object { $_.Destination })
$dataMountStatus = "UNAVAILABLE"
if ($mountDestinations -contains "/files/data") {
    $dataMountStatus = "AVAILABLE"
}
$workflowMountStatus = "UNAVAILABLE"
if ($mountDestinations -contains "/files/workflows") {
    $workflowMountStatus = "AVAILABLE"
}

$volumeStatus = "NOT FOUND"
& docker volume inspect $volumeName *> $null
if ($LASTEXITCODE -eq 0) {
    $volumeStatus = $volumeName
}

Write-StatusLine -Name "n8n Container" -Value $runningStatus
Write-StatusLine -Name "Container ID" -Value $containerId
Write-StatusLine -Name "Image" -Value ([string]$container.Config.Image)
Write-StatusLine -Name "Exposed Ports" -Value $portText
Write-StatusLine -Name "n8n URL" -Value "http://localhost:5678"
Write-StatusLine -Name "Data Mount" -Value $dataMountStatus
Write-StatusLine -Name "Workflow Mount" -Value $workflowMountStatus
Write-StatusLine -Name "Persistent Volume" -Value $volumeStatus

if (-not $container.State.Running) {
    exit 1
}
exit 0
