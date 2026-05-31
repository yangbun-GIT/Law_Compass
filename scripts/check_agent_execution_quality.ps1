param(
  [switch]$SkipDockerBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Label,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command
  )

  Write-Host ""
  Write-Host "==> $Label"
  & $Command
  $exitCode = $LASTEXITCODE
  if ($null -ne $exitCode -and $exitCode -ne 0) {
    throw "$Label failed with exit code $exitCode"
  }
}

Push-Location $RepoRoot
try {
  if (-not $SkipDockerBuild) {
    Invoke-Checked "Docker compose build/start" { docker compose up --build -d }
  }

  Invoke-Checked "Agent full P0-P11 execution quality suite" {
    docker compose exec -T agent python -m pytest tests -q
  }

  Invoke-Checked "Agent quality source compile" {
    docker compose exec -T agent python -m compileall app scripts tests
  }

  Write-Host ""
  Write-Host "check_agent_execution_quality=passed"
} finally {
  Pop-Location
}
